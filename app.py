from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
import io
import gc  # Pour le garbage collector

# Importation de la version corrigée qui est compatible avec uvloop sur Render.com
from fixed_signature_utils import (
    get_column_value, 
    get_formula_value,
    extract_pdf_asset_ids, 
    get_asset_public_url,
    transfert_file,
    add_scan_effects_minimal,
    sign_pdf_url_and_transfer,
    A4_WIDTH_PT, 
    A4_HEIGHT_PT,
    add_scan_effects
)
from Leyton_depot import deposit_single_item, change_status_simple
import fitz  # PyMuPDF
from PIL import Image
import requests

api_key = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjYwMTk5NDc0OSwiYWFpIjoxMSwidWlkIjo4Mjc3MzU1MCwiaWFkIjoiMjAyNS0xMi0zMFQxODo1NzoxNS40NTJaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MTYxMTUyOTAsInJnbiI6ImV1YzEifQ.1FETxKZKpyljE5VGK3q7qDJ4tuUiayxOm7C7dnyEsXg"  # Remplacez par votre token API

app = FastAPI(
    title="PDF Signature API",
    description="API for signing PDF documents from Monday.com",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IDRequest(BaseModel):
    item_id: int

@app.post("/sign-pdf/")
async def scann(request: Dict[Any, Any]):
    try :
        """Simple endpoint that receives a single item_id and returns it (echo).

        Use this to test sending a single ID to the API.
        """

        j = request['event']['pulseId']
        column_id_1 = "file_mkvywwf5"
        column_id_2 = "file_mkvyaef0"
        
        s_1 = get_column_value(api_key, [j], column_id_1)
        ids_1 = extract_pdf_asset_ids(s_1)  # -> [(assetId, fileName), ...]
        
        
        s_2 = get_column_value(api_key, [j], column_id_2)
        ids_2 = extract_pdf_asset_ids(s_2)  # -> [(assetId, fileName), ...]
        print(ids_2)
        for asset_id, base_name in ids_1:
            url = get_asset_public_url(api_key, asset_id)
            print(url)
            sign_pdf_url_and_transfer(
                pdf_url=url,
                base_filename=base_name,           # "E1-3-3 FACTURA.pdf" par ex.
                item_id=j,
                column_id=column_id_1,
                p12_path="signature/ronald/Certificat_Digital.p12",
                p12_password=b"1234",
                do_compress=True,                  # désactive si tu veux garder la source
                compress_dpi=150,                  # DPI équilibré (150 au lieu de 300)
                compress_quality=85,               # Qualité équilibrée (85 au lieu de 95)
                sig_box=(400, 600, 550, 700),      # nouvelle position dans la zone bleue en bas à droite
                field_name="Signature1",
                signed_suffix=" SIGNÉ",            # tu peux mettre " SIGNED" si tu préfères
                stamp_text="Firmado por: %(signer)s\nFecha: %(ts)s",
            )
        for asset_id, base_name in ids_2:
            url = get_asset_public_url(api_key, asset_id)
            print(url)
            sign_pdf_url_and_transfer(
                pdf_url=url,
                base_filename=base_name,           # "E1-3-3 FACTURA.pdf" par ex.
                item_id=j,
                column_id=column_id_2,
                p12_path="signature/ronald/Certificat_Digital.p12",
                p12_password=b"1234",
                do_compress=True,                  # désactive si tu veux garder la source
                compress_dpi=150,                  # DPI équilibré (150 au lieu de 300)
                compress_quality=85,               # Qualité équilibrée (85 au lieu de 95)
                sig_box=(400, 600, 550, 700),      # nouvelle position dans la zone bleue en bas à droite
                field_name="Signature1",
                signed_suffix=" SIGNÉ",            # tu peux mettre " SIGNED" si tu préfères
                stamp_text="Firmado por: %(signer)s\nFecha: %(ts)s",
            )
    except:
        return request
    
#
#@app.post("/sign-v2/")
#async def scann(request: Dict[Any, Any]):
#    """Simple endpoint that receives a single item_id and returns it (echo).
#
#    Use this to test sending a single ID to the API.
#    """
#    
#    j = request['event']['pulseId']
#    column_id = "dup__of_cee_final_mkmqz3vm"
#    s = get_column_value(api_key, [j], column_id)
#    signataires = {'Yassine': ['1234', 'signature/Yassine/AL_KHAITI_MOHAMMED_YASSINE___Y8886816K.p12'], #'Zakaria': ['Zaki1204', 'signature/nanou/10965016_identity.p12']}
#    signataire = get_column_value(api_key, [j], "color_mkvkh9af")[str(j)][0]['text']
#    
#    print(signataire)
#    print(s)
#    ids = extract_pdf_asset_ids(s)  # -> [(assetId, fileName), ...]
#    print(ids)
#    for asset_id, base_name in ids:
#        url = get_asset_public_url(api_key, asset_id)
#        print(url)
#        sign_pdf_url_and_transfer(
#            pdf_url=url,
#            base_filename=base_name,           # "E1-3-3 FACTURA.pdf" par ex.
#            item_id=j,
#            column_id="file_mkntx4fq",
#            p12_path=signataires[signataire][1],
#            p12_password=signataires[signataire][0].encode(),
#            do_compress=True,                  # désactive si tu veux garder la source
#            compress_dpi=150,                  # DPI équilibré (150 au lieu de 300)
#            compress_quality=85,               # Qualité équilibrée (85 au lieu de 95)
#            sig_box=(400, 600, 550, 700),      # nouvelle position dans la zone bleue en bas à droite
#            field_name="Signature1",
#            signed_suffix=" SIGNÉ",            # tu peux mettre " SIGNED" si tu préfères
#            stamp_text="Firmado por: %(signer)s\nFecha: %(ts)s",
#        )
#
# 
#
#@app.post("/sign-v3/")
#async def scann(request: Dict[Any, Any]):
#    """Simple endpoint that receives a single item_id and returns it (echo).
#
#    Use this to test sending a single ID to the API.
#    """
#    
#    j = request['event']['pulseId']
#    column_id = "fichier_mkmf8fcy"
#    s = get_column_value(api_key, [j], column_id)
#    ids = extract_pdf_asset_ids(s)  # -> [(assetId, fileName), ...]
#    print(ids)
#    for asset_id, base_name in ids:
#        url = get_asset_public_url(api_key, asset_id)
#        print(url)
#        sign_pdf_url_and_transfer(
#            pdf_url=url,
#            base_filename=base_name,           # "E1-3-3 FACTURA.pdf" par ex.
#            item_id=j,
#            column_id="file_mks32qy",
#            p12_path="signature/nanou/10965016_identity.p12",
#            p12_password=b"123456",
#            do_compress=True,                  # désactive si tu veux garder la source
#            compress_dpi=150,                  # DPI équilibré (150 au lieu de 300)
#            compress_quality=85,               # Qualité équilibrée (85 au lieu de 95)
#            sig_box=(400, 600, 550, 700),      # nouvelle position dans la zone bleue en bas à droite
#            field_name="Signature1",
#            signed_suffix=" SIGNÉ",            # tu peux mettre " SIGNED" si tu préfères
#            stamp_text="Firmado por: %(signer)s\nFecha: %(ts)s",
#        )
#    





@app.get("/")
async def root():
    return {"message": "Welcome to the PDF Signature API!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}



@app.post("/scann-pdf/")
async def scann(request: Dict[Any, Any]):
    try:
        # Récupérer l'ID depuis le webhook Monday.com
        j = request['event']['pulseId']
        
        # Traiter les deux colonnes
        column_ids = ["file_mkvy892y", "file_mkvy8sp5"]
        all_processed_files = []
        
        for column_id in column_ids:
            # Récupérer les informations de la colonne avec limite de mémoire
            s = get_column_value(api_key, [j], column_id)
            if not s:
                print(f"No column data found for column {column_id}")
                continue  # Passer à la colonne suivante

            # Extraire les IDs des PDFs
            ids = extract_pdf_asset_ids(s)
            if not ids:
                print(f"No PDF files found in column {column_id}")
                continue  # Passer à la colonne suivante
            
            # Libérer la mémoire
            del s
            
            # Force le garbage collector
            gc.collect()
            
            # Dimensions A4 optimisées (72 dpi)
            # A4 = 210mm x 297mm = 595 x 842 points à 72 dpi
            A4_WIDTH_PT = 595
            A4_HEIGHT_PT = 842
        
            # Dimensions optimales pour A4 à différentes résolutions
            # 72 dpi -> 595x842 pixels
            # 100 dpi -> 827x1169 pixels
            # 150 dpi -> 1240x1754 pixels
            
            processed_files = []
            for asset_id, file_name in ids:
                try:
                    # 1. Obtenir l'URL du fichier
                    url = get_asset_public_url(api_key, asset_id)
                    if not url:
                        continue
                    
                    # Télécharger le PDF en mode streaming (économie de mémoire)
                    resp = requests.get(url, stream=True)
                    resp.raise_for_status()
                    
                    # Ouvrir le PDF en streaming
                    pdf_document = fitz.open(stream=resp.raw.read(), filetype="pdf")
                    total_pages = len(pdf_document)
                    
                    # Créer un nouveau PDF directement
                    output_pdf = fitz.open()
                    
                    # 2. Traiter le PDF page par page (économie de mémoire)
                    for page_num in range(total_pages):
                        # Libérer la mémoire à chaque itération
                        gc.collect()
                        
                        # Extraire une page
                        page = pdf_document[page_num]
                        
                        # Résolution ÉQUILIBRÉE pour le scan A4 (150 dpi pour un bon compromis)
                        zoom = 150 / 72.0  # 150 dpi (moitié de 300 dpi)
                        mat = fitz.Matrix(zoom, zoom)
                        
                        # Pixmap amélioré avec colorspace RGB précis
                        pix = page.get_pixmap(matrix=mat, alpha=False, colorspace=fitz.csRGB)
                        
                        # Convertir en image Pillow
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        
                        # Appliquer effet scanner QUALITÉ ÉQUILIBRÉE
                        img = add_scan_effects_minimal(img, quality="balanced")
                        
                        # Convertir en JPEG en mémoire avec qualité équilibrée
                        temp_buffer = io.BytesIO()
                        img.save(temp_buffer, format="JPEG", quality=85, optimize=True, subsampling=0)
                        img_data = temp_buffer.getvalue()
                        
                        # Libérer la mémoire de l'image
                        del img
                        
                        # Créer nouvelle page A4
                        new_page = output_pdf.new_page(width=A4_WIDTH_PT, height=A4_HEIGHT_PT)
                        
                        # Insérer l'image compressée
                        rect = fitz.Rect(0, 0, A4_WIDTH_PT, A4_HEIGHT_PT)
                        new_page.insert_image(rect, stream=img_data)
                        
                        # Libérer la mémoire
                        del img_data
                        del temp_buffer
                        
                    # 3. Compression finale du PDF optimisée pour un BON ÉQUILIBRE taille/qualité
                    output_buffer = io.BytesIO()
                    output_pdf.save(output_buffer, 
                        garbage=3,           # Nettoyage modéré
                        deflate=True,        # Compression
                        clean=True,          # Supprimer les métadonnées inutiles
                        deflate_images=True, # Compresser les images
                        deflate_fonts=True,  # Compression des polices
                        pretty=False         # Pas de formatage joli (économie d'espace)
                    )
                    output_buffer.seek(0)
                    
                    # 4. Fermer les documents PDF pour libérer la mémoire
                    output_pdf.close()
                    pdf_document.close()
                    
                    # 5. Upload du fichier compressé
                    transfert_file(
                        output_buffer, 
                        j, 
                        column_id,
                        file_name
                    )
                    
                    # 6. Libérer la mémoire
                    del output_buffer
                    
                    processed_files.append(f"{file_name} -> {column_id}")
                    
                    # Force la libération de mémoire après chaque fichier
                    gc.collect()

                except Exception as e:
                    print(f"Error processing file {file_name} for column {column_id}: {str(e)}")
                    # Libérer la mémoire en cas d'erreur
                    gc.collect()
                    continue
            
            # Ajouter les fichiers traités pour cette colonne à la liste complète
            all_processed_files.extend(processed_files)
            print(f"Processed {len(processed_files)} files for column {column_id}")

        return {
            "status": "success",
            "message": f"Processed {len(all_processed_files)} files across {len(column_ids)} columns",
            "processed_files": all_processed_files
        }    
    except Exception as e:
        print(f"Error in webhook processing: {str(e)}")
        print("Request data:", str(request)[:200])  # Limiter la taille des logs
        #return {"error": str(e)}
        return request


@app.post("/depot_leyton/")
async def depot(request: Dict[Any, Any]):
    try:
        print("Received request:", request)
        j = request['event']['pulseId']
        
        lot=get_column_value(api_key, [j], "text_mkvy320e")[str(j)][0]['text']
        deposit_single_item(
            item_id=j,          # ID de l'item Monday
            lot_folder_name=lot,    # dossier de lot (créé/cherché sous ROOT_PARENT_ID)
            root_parent_id="18Mjsu2-uJqeZKqUYeWWwSOr8CBPGemEx",
            start_e_id=None,             # None => auto-incrément ACT_{id}
            auto_increment=True,         # calcule max(ACT_{id})+1 dans le lot
            update_status=True           # MAJ statut si au moins 1 upload OK
        )
        return {"message": "deposé avec succé!"}
    except Exception as e:
        print(f"Error in depot_leyton: {str(e)}")
        return request



#@app.post("/RES_CONDITION/")
#async def depot(request: Dict[Any, Any]):
#    try:
#        print("Received request:", request)
#        j = request['event']['pulseId']
#        
#        res_type=get_formula_value(api_key, j, "formula_mkp5k1dx")
#        print(res_type)
#        if float(res_type) > 25 :
#            change_status_simple(api_key, 9962467444, j, "color_mkp6dx3h", "RES010")
#        else:
#            change_status_simple(api_key, 9962467444, j, "color_mkp6dx3h", "RES020")
#        return {"message": "deposé avec succé!"}
#    except Exception as e:
#        print(f"Error in depot_leyton: {str(e)}")
#        return request
