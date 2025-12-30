"""
Module de fonctions utilitaires pour la signature de PDF et les effets de numérisation
Corrige le problème uvloop sur Render.com
"""

# Standard library imports
import io
import json
import os
import random
import tempfile
from typing import Tuple, Optional
import threading
import concurrent.futures

# Third-party imports
import requests
import numpy as np
import nest_asyncio
import fitz  # PyMuPDF
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
from fpdf import FPDF

# PyHanko imports
import asyncio
from pyhanko.sign import signers
from pyhanko.sign.signers.pdf_signer import PdfSigner, PdfSignatureMetadata
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.fields import SigFieldSpec, append_signature_field, VisibleSigSettings
from pyhanko.stamp.text import TextStampStyle
from pyhanko.pdf_utils.text import TextBoxStyle

api_key = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjYwMTk5NDc0OSwiYWFpIjoxMSwidWlkIjo4Mjc3MzU1MCwiaWFkIjoiMjAyNS0xMi0zMFQxODo1NzoxNS40NTJaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MTYxMTUyOTAsInJnbiI6ImV1YzEifQ.1FETxKZKpyljE5VGK3q7qDJ4tuUiayxOm7C7dnyEsXg"  # Remplacez par votre token API

# -------------------------------------------------------------------
# Compression optimisée pour la qualité (PyMuPDF + Pillow)
# -------------------------------------------------------------------
def compress_pdf_bytes(pdf_bytes: bytes, quality: str = "balanced", target_dpi: int = 150, jpeg_quality: int = 85) -> bytes:
    """
    Compresse un PDF en mémoire en réduisant la résolution des images tout en conservant une bonne qualité.
    """
    import io
    import fitz  # PyMuPDF
    from PIL import Image, ImageEnhance

    # Ajuster les paramètres selon le niveau de qualité
    if quality == "minimum":
        target_dpi = 90
        jpeg_quality = 50
    elif quality == "balanced":
        target_dpi = 150
        jpeg_quality = 85
    elif quality == "high":
        target_dpi = 200
        jpeg_quality = 90
    elif quality == "premium":
        target_dpi = 250
        jpeg_quality = 95
    elif quality == "ultra":
        target_dpi = 300  # Résolution ultra-haute
        jpeg_quality = 100  # Qualité maximale

    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    dst = fitz.open()

    # On rend les pages à target_dpi, puis on crée des pages PDF en POINTS (72 dpi)
    for page in src:
        zoom = target_dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        # Utiliser colorspace=fitz.csRGB pour une meilleure qualité des couleurs
        pix = page.get_pixmap(matrix=mat, alpha=False, colorspace=fitz.csRGB)

        # Convertir en image Pillow
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Améliorer la netteté pour le texte
        sharpness = ImageEnhance.Sharpness(img)
        img = sharpness.enhance(1.2)  # Légèrement plus net
        
        # Améliorer le contraste
        contrast = ImageEnhance.Contrast(img)
        img = contrast.enhance(1.05)  # Légèrement plus contrasté
        
        # Encode en JPEG avec haute qualité
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True, 
                 subsampling=0)  # Subsampling=0 pour meilleure qualité du texte
        img_bytes = buf.getvalue()

        # ⚠️ Dimensions PDF en points (72 dpi), pas en pixels
        width_pt  = pix.width  * 72.0 / target_dpi
        height_pt = pix.height * 72.0 / target_dpi

        rect = fitz.Rect(0, 0, width_pt, height_pt)
        new_page = dst.new_page(width=width_pt, height=height_pt)
        new_page.insert_image(rect, stream=img_bytes, keep_proportion=False)

    # Enregistrement avec paramètres de qualité
    out = io.BytesIO()
    dst.save(out, 
        garbage=3,              # Niveau de nettoyage modéré (4 = agressif, 1 = minimal)
        deflate=True,           # Compression du contenu
        clean=True,             # Suppression des données obsolètes
        deflate_images=False,   # Ne pas re-compresser les images (déjà optimisées)
        deflate_fonts=True,     # Compresser les polices
        pretty=False            # Format compact (non-indenté)
    )
    dst.close()
    src.close()
    return out.getvalue()


# ------------------------------------------------------
# Utilitaire: fabriquer un nom "<base> SIGNÉ.pdf" propre
# ------------------------------------------------------
def make_signed_filename(base_filename: str, suffix: str = " SIGNÉ") -> str:
    name = base_filename.strip()
    # éviter doublons: si le nom contient déjà le suffixe (insensible à la casse)
    if suffix.lower() in name.lower():
        return name if name.lower().endswith(".pdf") else f"{name}.pdf"

    if name.lower().endswith(".pdf"):
        return name[:-4] + f"{suffix}.pdf"
    return name + f"{suffix}.pdf"


# ----------------------------------------------------------------------
# Signature visible (tampon texte) en bas-droite
# ----------------------------------------------------------------------

# --- ASYNC pur ---
async def _sign_pdf_bytes_visible_async(
    pdf_bytes: bytes,
    p12_path: str,
    p12_password: bytes,
    sig_box: Tuple[int, int, int, int] = (300, 470, 500, 530),
    field_name: str = "Signature1",
    stamp_text: str = "Firmado por: %(signer)s\nFecha: %(ts)s",
) -> bytes:
    simple_signer = signers.SimpleSigner.load_pkcs12(p12_path, passphrase=p12_password)

    text_style = TextStampStyle(
        stamp_text=stamp_text,
        text_box_style=TextBoxStyle(font_size=10),
        background=None,
        border_width=0
    )
    meta = PdfSignatureMetadata(field_name=field_name)

    inp = io.BytesIO(pdf_bytes)
    writer = IncrementalPdfFileWriter(inp)

    # ⚡ Forcer la création d'un champ visible via new_field_spec
    new_field_spec = SigFieldSpec(
        sig_field_name=field_name,
        box=sig_box,
        visible_sig_settings=VisibleSigSettings(rotate_with_page=True),
    )

    pdf_signer = PdfSigner(
        signature_meta=meta,
        signer=simple_signer,
        new_field_spec=new_field_spec,   # <-- clé : on ne s'appuie pas sur append_signature_field
        stamp_style=text_style
    )

    out = io.BytesIO()
    await pdf_signer.async_sign_pdf(writer, output=out)  # pas d'asyncio.run ici
    return out.getvalue()


# --- WRAPPER CORRIGÉ POUR RENDER.COM (COMPATIBLE UVLOOP) ---
def sign_pdf_bytes_visible(
    pdf_bytes: bytes,
    p12_path: str,
    p12_password: bytes,
    sig_box: Tuple[int, int, int, int] = (300, 470, 500, 530),
    field_name: str = "Signature1",
    stamp_text: str = "Firmado por: %(signer)s\nFecha: %(ts)s",
) -> bytes:
    """
    Version corrigée qui fonctionne avec uvloop sur Render.com
    """
    coro = _sign_pdf_bytes_visible_async(
        pdf_bytes=pdf_bytes,
        p12_path=p12_path,
        p12_password=p12_password,
        sig_box=sig_box,
        field_name=field_name,
        stamp_text=stamp_text,
    )
    
    # Méthode fiable : exécuter dans un thread séparé avec un nouveau loop
    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    
    # Exécuter dans un thread séparé pour éviter les problèmes avec uvloop
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_new_loop)
        return future.result()


# ---------------------------------------------------------------------------------------
# Pipeline complet: URL -> (download) -> (compress?) -> signature -> transfert_file(...)
# ---------------------------------------------------------------------------------------
def sign_pdf_url_and_transfer(
    pdf_url: str,
    base_filename: str,            # "nomination qui a déjà" (ex: "E1-3-3 FACTURA.pdf")
    item_id: int,
    column_id: str,                # ex: "file_mkp6r6am"
    p12_path: str,
    p12_password: bytes,
    *,
    do_compress: bool = True,
    compress_dpi: int = 144,
    compress_quality: int = 60,
    sig_box: Tuple[int, int, int, int] = (300, 470, 500, 530),
    field_name: str = "Signature1",
    signed_suffix: str = " SIGNÉ",
    stamp_text: str = "Firmado por: %(signer)s\nFecha: %(ts)s",
):
    # 1) Télécharger
    r = requests.get(pdf_url, timeout=60)
    r.raise_for_status()
    pdf_bytes = r.content

    # 2) (Optionnel) compresser AVANT la signature
    if do_compress:
        pdf_bytes = compress_pdf_bytes(pdf_bytes, quality="balanced", target_dpi=compress_dpi, jpeg_quality=compress_quality)

    # 3) Signer (visible)
    signed_bytes = sign_pdf_bytes_visible(
        pdf_bytes,
        p12_path=p12_path,
        p12_password=p12_password,
        sig_box=sig_box,
        field_name=field_name,
        stamp_text=stamp_text,
    )

    # 4) Nom final = "nomination qui a déjà" + " SIGNÉ"
    final_name = make_signed_filename(base_filename, suffix=signed_suffix)

    # 5) Upload vers CRM
    file_like = io.BytesIO(signed_bytes)
    transfert_file(file_like, item_id, column_id, final_name)  # <-- ta fonction existante

    print(f"✅ Upload OK: {final_name} -> item {item_id} / {column_id}")
    return final_name


def get_column_value(api_key, item_ids, column_id):
    api_url = "https://api.monday.com/v2"
    # item_ids doit être une liste d'IDs d'items, column_id est l'ID de la colonne
    query = """
    query {
      items(ids: [%s]) {
        id
        column_values(ids: ["%s"]) {
          id
          value
          text
          type
        }
      }
    }
    """ % (",".join(str(i) for i in item_ids), column_id)

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    response = requests.post(
        api_url,
        json={"query": query},
        headers=headers
    )

    data = response.json()
    values_by_item = {}
    for item in data["data"]["items"]:
        values_by_item[item["id"]] = item["column_values"]
    return values_by_item


def extract_pdf_asset_ids(data):
    """
    Parcourt le dictionnaire renvoyé par l'API Monday.com et renvoie
    la liste des assetId pour les fichiers dont le nom se termine par '.pdf'.
    """
    asset_ids = []
    for column_values in data.values():
        for entry in column_values:
            # 'value' est une chaîne JSON, on la parse
            payload = json.loads(entry.get('value', '{}'))
            for f in payload.get('files', []):
                # Vérifie l'extension en minuscules
                if f.get('name', '').lower().endswith('.pdf'):
                    asset_ids.append([f.get('assetId'),f.get('name')+'_SCANNE'])
    return asset_ids


def transfert_file(file,ID_REF,column_id,nom):
    try :
        nom=str(nom)
    except :
        nom=''
    url = "https://api.monday.com/v2/file"
    
    payload={'query': 'mutation add_file($file: File!) {add_file_to_column (item_id:' +str(ID_REF)+', column_id:"'+column_id+'" file: $file) {id}}','map': '{"image":"variables.file"}'}
    files=[
      ('image',(nom+'.pdf',file,'application/octet-stream'))
    ]
    headers = {
      'Authorization': api_key,
    }
    
    response = requests.request("POST", url, headers=headers, data=payload, files=files,stream=True,allow_redirects=True)

    print(response.text)
    return response


def get_asset_public_url(api_key: str, asset_id: int) -> str:
    """
    Récupère le lien public (public_url) dun fichier (asset) dans Monday.com.
    """
    url = "https://api.monday.com/v2"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    query = f"""
    {{
      assets(ids: [{asset_id}]) {{
        public_url
      }}
    }}
    """

    response = requests.post(url, headers=headers, json={"query": query})
    response.raise_for_status()
    data = response.json()

    try:
        return data['data']['assets'][0]['public_url']
    except Exception as e:
        print("Erreur lors de la récupération du public_url :", e)
        return None


# Configuration section
DPI = 200  # Qualité de l'image (150-300 recommandé)
SCAN_QUALITY = "realistic"  # Options: "light", "medium", "heavy", "realistic", "old_scanner"
KEEP_TEMP_IMAGES = False  # Mettre True pour garder les images temporaires

# Dimensions format A4 standard en points (72 dpi)
A4_WIDTH_PT = 595
A4_HEIGHT_PT = 842

# Version haute qualité de add_scan_effects pour de meilleurs PDF
def add_scan_effects_minimal(image, quality="high"):
    """
    Version optimisée des effets de scan pour une meilleure qualité
    tout en conservant une bonne performance mémoire
    """
    # Paramètres selon la qualité désirée
    if quality == "minimum":
        # Configuration minimale pour la mémoire
        brightness_factor = 1.05
        contrast_factor = 1.1
        blur_radius = 0.2
        saturation = 0.8
        jpeg_quality = 40
    elif quality == "balanced":
        # Équilibre entre qualité et performance
        brightness_factor = 1.03
        contrast_factor = 1.12
        blur_radius = 0.3
        saturation = 0.85
        jpeg_quality = 65
    elif quality == "high":
        # Haute qualité pour documents importants
        brightness_factor = 1.02
        contrast_factor = 1.15
        blur_radius = 0.25
        saturation = 0.9
        jpeg_quality = 80
        # Appliquer léger sharpening pour améliorer la netteté du texte
        image = image.filter(ImageFilter.SHARPEN)
    elif quality == "premium":
        # Qualité premium pour documents officiels
        brightness_factor = 1.01
        contrast_factor = 1.12
        blur_radius = 0.2
        saturation = 0.95
        jpeg_quality = 92
        # Amélioration de la netteté avec filtres avancés
        image = image.filter(ImageFilter.SHARPEN)
        image = image.filter(ImageFilter.EDGE_ENHANCE)
    else: # quality == "ultra" - Qualité maximale pour archivage
        brightness_factor = 1.0
        contrast_factor = 1.15
        blur_radius = 0.0  # Pas de flou pour préserver tous les détails
        saturation = 1.0   # Conserver les couleurs originales
        jpeg_quality = 100
        
        # Triple amélioration de la netteté pour détails ultra-fins
        sharpness = ImageEnhance.Sharpness(image)
        image = sharpness.enhance(1.5)  # Netteté augmentée de 50%
        image = image.filter(ImageFilter.EDGE_ENHANCE_MORE)
        
        # Améliorer les contours pour le texte
        image = image.filter(ImageFilter.DETAIL)
    
    # 1. Ajuster la luminosité et le contraste (étapes essentielles)
    brightness = ImageEnhance.Brightness(image)
    image = brightness.enhance(brightness_factor)
    
    contrast = ImageEnhance.Contrast(image)
    image = contrast.enhance(contrast_factor)
    
    # 2. Flou léger (simuler le scan)
    if blur_radius > 0:
        image = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    # 3. Ajuster la saturation (simuler les couleurs du scanner)
    color = ImageEnhance.Color(image)
    image = color.enhance(saturation)
    
    # 4. Améliorer la netteté pour le texte (pour qualité premium/high)
    if quality in ["premium", "high"]:
        # Deuxième passe de sharpening pour le texte
        sharpness = ImageEnhance.Sharpness(image)
        image = sharpness.enhance(1.3)  # Valeur > 1 = plus net
    
    # 5. Compression JPEG en mémoire avec qualité adaptée
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=jpeg_quality, optimize=True)
    buffer.seek(0)
    image = Image.open(buffer)
    
    return image

# Fonction complète d'effet de scan
def add_scan_effects(image, quality="realistic"):
    """
    Ajoute des effets pour simuler un document scanné
    """
    # Paramètres selon la qualité
    if quality == "light":
        rotation_range = 0.3
        noise_level = 1
        blur_radius = 0.2
        brightness_range = (0.98, 1.02)
        contrast_range = (1.05, 1.15)
        saturation = 0.9
        jpeg_quality = 90
    elif quality == "heavy":
        rotation_range = 1.0
        noise_level = 4
        blur_radius = 0.5
        brightness_range = (0.90, 1.10)
        contrast_range = (1.2, 1.4)
        saturation = 0.6
        jpeg_quality = 75
    elif quality == "realistic":
        rotation_range = 0.8
        noise_level = 3
        blur_radius = 0.4
        brightness_range = (0.92, 1.08)
        contrast_range = (1.15, 1.35)
        saturation = 0.7
        jpeg_quality = 80
    elif quality == "old_scanner":
        rotation_range = 1.2
        noise_level = 5
        blur_radius = 0.6
        brightness_range = (0.88, 1.12)
        contrast_range = (1.25, 1.45)
        saturation = 0.5
        jpeg_quality = 70
    else:  # medium
        rotation_range = 0.5
        noise_level = 2
        blur_radius = 0.3
        brightness_range = (0.95, 1.05)
        contrast_range = (1.1, 1.3)
        saturation = 0.8
        jpeg_quality = 85
    
    # 1. Légère rotation aléatoire
    angle = random.uniform(-rotation_range, rotation_range)
    image = image.rotate(angle, fillcolor='white', expand=False)
    
    # 2. Ajouter des bordures sombres subtiles
    width, height = image.size
    mask = Image.new('L', (width, height), 255)
    draw = ImageDraw.Draw(mask)
    for i in range(5):
        opacity = 255 - i * 10
        draw.rectangle([i, i, width-i, height-i], outline=opacity)
    image = Image.composite(image, Image.new('RGB', (width, height), (250, 250, 250)), mask)
    
    # 3. Ajuster la luminosité et le contraste
    brightness = ImageEnhance.Brightness(image)
    image = brightness.enhance(random.uniform(*brightness_range))
    
    contrast = ImageEnhance.Contrast(image)
    image = contrast.enhance(random.uniform(*contrast_range))
    
    # 4. Ajouter du bruit
    img_array = np.array(image)
    noise = np.random.normal(0, noise_level * 1.5, img_array.shape)
    img_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    image = Image.fromarray(img_array)
    
    # 5. Distorsion légère pour "realistic" et "old_scanner"
    if quality in ["realistic", "old_scanner"]:
        img_array = np.array(image)
        rows, cols = img_array.shape[:2]
        for i in range(rows):
            shift = int(2 * np.sin(2 * np.pi * i / 150))
            img_array[i] = np.roll(img_array[i], shift, axis=0)
        image = Image.fromarray(img_array)
    
    # 6. Flou
    image = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    # 7. Ajuster la saturation
    color = ImageEnhance.Color(image)
    image = color.enhance(saturation)
    
    # 8. Lignes de scan subtiles
    if quality in ["realistic", "old_scanner"]:
        img_array = np.array(image)
        for y in range(0, height, 50):
            if random.random() > 0.98:
                img_array[y:y+1, :] = img_array[y:y+1, :] * 0.95
        image = Image.fromarray(img_array.astype(np.uint8))
    
    # 9. Compression JPEG
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp_path = tmp.name
        image.save(tmp_path, 'JPEG', quality=jpeg_quality)
    
    with Image.open(tmp_path) as temp_image:
        image = temp_image.copy()
    os.unlink(tmp_path)
    
    return image


def get_formula_value(api_token: str, item_id: int, formula_column_id: str) -> str | None:
    """
    Return the computed value of a Formula column for a given item.
    Prefers `display_value` (formatted) and falls back to `text` if needed.
    """
    api_url = "https://api.monday.com/v2"
    query = """
    query ($itemIds: [ID!], $colIds: [String!]) {
      version { value }  # lets you confirm which API version was used
      items (ids: $itemIds) {
        id
        column_values(ids: $colIds) {
          id
          text
          ... on FormulaValue {
            display_value
            value
          }
        }
      }
    }
    """
    variables = {"itemIds": [str(item_id)], "colIds": [formula_column_id]}
    headers = {
        "Authorization": api_token,
        "Content-Type": "application/json"
    }

    resp = requests.post(api_url, headers=headers, json={"query": query, "variables": variables}, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    # basic safety checks
    items = (data.get("data", {}).get("items") or [])
    if not items:
        return None
    cols = items[0].get("column_values") or []
    if not cols:
        return None

    cv = cols[0]
    # Prefer nicely formatted result if present (e.g., with units/currency)
    return cv.get("display_value") or cv.get("text") or None

