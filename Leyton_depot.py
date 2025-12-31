
# ====================== User Config ======================
import os
MONDAY_API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjYwMTk5NDc0OSwiYWFpIjoxMSwidWlkIjo4Mjc3MzU1MCwiaWFkIjoiMjAyNS0xMi0zMFQxODo1NzoxNS40NTJaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MTYxMTUyOTAsInJnbiI6ImV1YzEifQ.1FETxKZKpyljE5VGK3q7qDJ4tuUiayxOm7C7dnyEsXg"  # Remplacez par votre token API
# -*- coding: utf-8 -*-
"""
Single-item deposit to Google Drive from Monday.com with:
- per-file dedicated column IDs (CEE FINAL / REGISTRO / PAGO have different columns)
- fully configurable matching rules per column (keywords, file types, pick strategy, fallbacks)
- strict folder existence check (avoid duplicate lot folders)
- ACT_{id} auto-increment

Prereqs:
pip install requests google-api-python-client google-auth-httplib2 google-auth-oauthlib
credentials.json in working dir (OAuth "Desktop app")
set MONDAY_API_KEY in environment (do not hardcode)
"""

# ====================== User Config ======================

BOARD_ID = 5001741596
TEXT_COLUMN_ID = "text_mkvehxzn"
STATUS_COLUMN_ID = "color_mkvxc381"
STATUS_VALUE = "Dossier déposé"
CREATE_LABEL_IF_MISSING = False

# Drive OAuth
SCOPES = ["https://www.googleapis.com/auth/drive"]
CREDENTIALS_PATH = "auth/credentials.json"
TOKEN_PATH = "auth/token.json"

# Upload options
SKIP_EXCEL_UPLOAD = True   # True => skip Excel uploads
DO_CREATE_DRIVE  = True    # False => dry run (no Drive calls)

# ------------- (A) Column IDs per file (EDIT ME) ----------------
# Donne un column_id distinct pour chaque type de fichier que tu veux récupérer.
# Mets les vrais IDs Monday de TON board.
COLUMN_IDS = {
    # E-1
    "CONTRATO":         "file_mkvy892y",
    # E-3
    "FICHA_RES020":     "file_mkvy7naj",
    "DECLARACION":      "file_mkvy8sp5",
    "FACTURA":          "file_mkvy87gx",
    "INFORME_FOTO":     "file_mkvyaef0",
    "CERTIFICADO_INST": "file_mkvywwf5",
    # E-3-6 (désormais sur DES COLONNES DISTINCTES)
    "CEE_FINAL":        "file_mkvy5f3n",   # <-- remplace par ton vrai column_id
    "REGISTRO":         "file_mkvywnbx",    # <-- remplace par ton vrai column_id
    "PAGO":             "file_mkvydbq5",        # <-- remplace par ton vrai column_id
    # E-4
    "DNI":              "file_mkvyb1g7",
    "EXCEL":            "file_mkvy6b1j",
}

# ------------- (B) Matching rules per column (EDIT AS NEEDED) -------------
# Pour chaque column_id, tu peux définir:
#  - include_any_of: liste de mots-clés (normalisés ; insensibles à la casse/accents)
#  - exclude_any_of: mots-clés à exclure
#  - file_types:    liste d’extensions autorisées (ex: ["pdf","jpg"]) ou ["any"]
#  - pick:          "latest" | "first" | "all"   (stratégie de sélection)
#  - max:           nombre max d’assets (si pick="all", on tronque à max si défini)
#  - fallbacks:     liste de règles simplifiées à essayer si aucune correspondance
#
# Si rien n’est défini pour un column_id -> règle par défaut:
#   file_types=["pdf"], pick="latest"
MATCH_RULES = {
    COLUMN_IDS["CONTRATO"]: {
        "include_any_of": ["scanne","scan","escaneado","escaneada","scannerisé"],
        "file_types": ["pdf"],
        "pick": "latest",
    },
    COLUMN_IDS["DECLARACION"]: {
        "include_any_of": ["scanne","scan"],
        "file_types": ["pdf"],
        "pick": "latest",
    },
    COLUMN_IDS["CERTIFICADO_INST"]: {
        "include_any_of": ["signe","firmado","signed"],
        "file_types": ["pdf"],
        "pick": "latest",
    },
    # --- E-3-6 (désormais séparées) ---
    COLUMN_IDS["CEE_FINAL"]: {
        "include_any_of": ["v3","final","cee"],
        "file_types": ["pdf"],
        "pick": "latest",
        "fallbacks": [
            {"file_types": ["pdf"], "pick": "latest"}  # si aucun mot-clé ne matche, prendre le dernier PDF
        ]
    },
    COLUMN_IDS["REGISTRO"]: {
        "include_any_of": ["solicitud de inscripcion","solicitud de registro","registro"],
        "file_types": ["pdf"],
        "pick": "latest",
        "fallbacks": [{"file_types": ["pdf"], "pick": "latest"}]
    },
    COLUMN_IDS["PAGO"]: {
        "include_any_of": ["modelo 046","046","pago","tasas"],
        "file_types": ["pdf"],
        "pick": "latest",
        "fallbacks": [{"file_types": ["pdf"], "pick": "latest"}]
    },
    # DNI : souvent multiples -> tout prendre
    COLUMN_IDS["DNI"]: {
        "file_types": ["any"],
        "pick": "all",
        "max": None,
    },
    # EXCEL : on filtrera par extension .xls/.xlsx (et SKIP_EXCEL_UPLOAD contrôle l’upload)
    COLUMN_IDS["EXCEL"]: {
        "file_types": ["xlsx","xls"],
        "pick": "all",
    },
}
# ==========================================================================


# ====================== Imports & base helpers ======================
import io, re, json, time
from typing import Optional, Dict, Any, List, Tuple

import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

MONDAY_API_URL = "https://api.monday.com/v2"

def _norm(s: Optional[str]) -> str:
    if not s: return ""
    import unicodedata
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return " ".join(s.lower().split())

def _file_ext(name: str) -> str:
    n = (name or "").lower()
    for ext in (".pdf",".jpg",".jpeg",".png",".xlsx",".xls",".docx",".doc",".txt"):
        if n.endswith(ext):
            return ext[1:]  # sans le point
    return ""

def _parse_column_value(value_str: Optional[str]) -> List[Dict[str, Any]]:
    if not value_str: return []
    try:
        obj = json.loads(value_str)
        return obj.get("files", []) or []
    except Exception:
        return []

# ====================== Monday API ======================
def get_item_name(api_key: str, item_id: int) -> str:
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    q = f"""
    query {{
      items(ids: [{item_id}]) {{ id name }}
    }}
    """
    r = requests.post(MONDAY_API_URL, headers=headers, json={"query": q}, timeout=60)
    r.raise_for_status()
    data = r.json()
    items = (data.get("data") or {}).get("items") or []
    return (items[0].get("name") if items else f"ITEM_{item_id}")

def get_columns_values(api_key: str, item_id: int, column_ids: List[str]) -> Dict[str, Any]:
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    cols = ",".join(f'"{cid}"' for cid in column_ids)
    query = f"""
    query {{
      items(ids: [{item_id}]) {{
        id
        column_values(ids: [{cols}]) {{
          id value text type
        }}
      }}
    }}
    """
    resp = requests.post(MONDAY_API_URL, headers=headers, json={"query": query}, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", {}).get("items", [])
    if not items: return {}
    arr = items[0].get("column_values", [])
    return {c["id"]: c for c in arr}

def get_assets_public_urls_map(api_key: str, asset_ids: List[int]) -> Dict[int, Optional[str]]:
    if not asset_ids: return {}
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    out: Dict[int, Optional[str]] = {}
    chunk = 50
    for i in range(0, len(asset_ids), chunk):
        ids_part = asset_ids[i:i+chunk]
        ids_str = ",".join(str(x) for x in ids_part)
        q = f"{{ assets(ids: [{ids_str}]) {{ id public_url }} }}"
        r = requests.post(MONDAY_API_URL, headers=headers, json={"query": q}, timeout=60)
        r.raise_for_status()
        data = r.json()
        assets = (data.get("data") or {}).get("assets") or []
        for a in assets:
            out[int(a["id"])] = a.get("public_url")
    return out

# ====================== Structure ======================
def generer_structure_lot(
    lot_numero: int,
    clients: List[Tuple[str, str]],
    start_id: int = 1
) -> Dict[str, Any]:
    def col(nom: str, column_id: str) -> Dict[str, str]:
        return {"nom": nom, "column_id": column_id}

    def build_structure_for_client(cid: int) -> List[Dict[str, Any]]:
        E = f"E{cid}"
        return [
            {"nom": f"{E}-1-CONVENIO CAE",
             "files": [col(f"{E}-1-1 CONTRATO CESION AHORROS", COLUMN_IDS["CONTRATO"])]},
            {"nom": f"{E}-2-DICTAMEN FAVORABLE E INFORME", "files": []},
            {"nom": f"{E}-3-DOCUMENTOS JUSTIFICATIVOS",
             "files": [
                 col(f"{E}-3-1 FICHA RES020 CUMPLIMENTADA", COLUMN_IDS["FICHA_RES020"]),
                 col(f"{E}-3-2 DECLARACION RESPONSABLE",    COLUMN_IDS["DECLARACION"]),
                 col(f"{E}-3-3 FACTURA",                    COLUMN_IDS["FACTURA"]),
                 col(f"{E}-3-4 INFORME FOTOGRÁFICO",       COLUMN_IDS["INFORME_FOTO"]),
                 col(f"{E}-3-5 CERTIFICADO INSTALADOR",     COLUMN_IDS["CERTIFICADO_INST"]),
                 # colonnes distinctes
                 col(f"{E}-3-6-1 CEE FINAL", COLUMN_IDS["CEE_FINAL"]),
                 col(f"{E}-3-6-2 REGISTRO",   COLUMN_IDS["REGISTRO"]),
                 col(f"{E}-3-6-3 PAGO",       COLUMN_IDS["PAGO"]),
             ]},
            {"nom": f"{E}-4-OTROS DOCUMENTOS JUSTIFICATIVOS",
             "files": [
                 col(f"{E}-4-DNI",   COLUMN_IDS["DNI"]),
                 col(f"{E}-4-EXCEL", COLUMN_IDS["EXCEL"]),
             ]},
        ]

    def dossier_name(auto_id: int, nomcomplet: str) -> str:
        return f"ACT_{auto_id}_{nomcomplet.upper().replace(' ', '_')}"

    lot_name = f"CLM_GE_{lot_numero:02d}"
    res: Dict[str, Any] = {"lot": {"numero": lot_numero, "nom": lot_name, "clients": []}}
    auto_id = start_id
    for nomcomplet, id_monday in clients:
        res["lot"]["clients"].append({
            "id": auto_id,
            "id_monday": str(id_monday),
            "nomcomplet": nomcomplet,
            "dossier_principal": dossier_name(auto_id, nomcomplet),
            "structure": build_structure_for_client(auto_id),
        })
        auto_id += 1
    return res

# ====================== Matching Engine ======================
def _apply_rule_on_pool(pool: List[Dict[str, Any]], rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Applique une règle de sélection sur la liste brute 'pool' (files[] d'une colonne Monday).
    Retourne une liste d'assets (peut être vide).
    """
    include_any = [_norm(k) for k in rule.get("include_any_of", []) or []]
    exclude_any = [_norm(k) for k in rule.get("exclude_any_of", []) or []]
    types      = [t.lower() for t in (rule.get("file_types") or ["pdf"])]
    pick       = (rule.get("pick") or "latest").lower()
    max_count  = rule.get("max")

    # 1) filtrage types
    def type_ok(x):
        if "any" in types: 
            return True
        ext = _file_ext(x.get("name",""))
        return ext in types

    # 2) filtrage mots-clés (include/exclude sur le nom normalisé)
    def kw_ok(x):
        nm = _norm(x.get("name",""))
        if include_any:
            if not any(k in nm for k in include_any):
                return False
        if exclude_any:
            if any(k in nm for k in exclude_any):
                return False
        return True

    cand = [x for x in pool if type_ok(x) and kw_ok(x)]

    # 3) tri par createdAt décroissant (si dispo)
    cand.sort(key=lambda z: z.get("createdAt", 0), reverse=True)

    # 4) stratégie pick
    if pick == "latest":
        cand = cand[:1]
    elif pick == "first":
        cand = cand[:1][::-1]  # s'il y a un ordre naturel ; sinon latest ≈ first à l'envers
    elif pick == "all":
        pass
    else:  # default to latest
        cand = cand[:1]

    # 5) max
    if max_count is not None and isinstance(max_count, int):
        cand = cand[:max_count]

    return cand

def _match_with_fallbacks(pool: List[Dict[str, Any]], main_rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    res = _apply_rule_on_pool(pool, main_rule)
    if res:
        return res
    for fb in main_rule.get("fallbacks", []) or []:
        # fallback hérite pas des includes/excludes par défaut, c'est volontaire
        fb_rule = {
            "include_any_of": fb.get("include_any_of", []),
            "exclude_any_of": fb.get("exclude_any_of", []),
            "file_types": fb.get("file_types", ["pdf"]),
            "pick": fb.get("pick", "latest"),
            "max": fb.get("max"),
        }
        res = _apply_rule_on_pool(pool, fb_rule)
        if res:
            return res
    return []

def _select_assets_for_column(column_id: str, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prend la liste 'files' d'une colonne Monday et applique la règle MATCH_RULES de 'column_id'.
    Renvoie une liste d'assets normalisés: [{asset_id, name}]
    """
    rule = MATCH_RULES.get(column_id, {"file_types": ["pdf"], "pick": "latest"})
    chosen = _match_with_fallbacks(files, rule)
    out: List[Dict[str, Any]] = []
    for it in chosen:
        aid = it.get("assetId")
        if aid is not None:
            out.append({"asset_id": int(aid), "name": it.get("name") or "file.bin"})
    return out

# ====================== Extraction par client ======================
def extract_assets_for_client(api_key: str, item_id: int, structure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # 1) collecter colonnes nécessaires (toutes distinctes désormais)
    needed_cols = []
    for sub in structure:
        for f in sub.get("files", []):
            cid = f.get("column_id")
            if cid:
                needed_cols.append(cid)
    unique_cols = sorted(set(needed_cols))

    # 2) fetch columns -> files[]
    colmap = get_columns_values(api_key, int(item_id), unique_cols)
    files_by_col: Dict[str, List[Dict[str, Any]]] = {}
    for cid in unique_cols:
        col_obj = colmap.get(cid, {})
        files_by_col[cid] = _parse_column_value(col_obj.get("value"))

    # 3) appliquer la règle par colonne
    result = []
    for sub in structure:
        sub_out = {"nom": sub.get("nom"), "files": []}
        for f in sub.get("files", []):
            name = f.get("nom", "")
            cid  = f.get("column_id", "")
            pool = files_by_col.get(cid, [])
            assets_list = _select_assets_for_column(cid, pool)
            sub_out["files"].append({"nom": name, "column_id": cid, "assets": assets_list})
        result.append(sub_out)
    return result

def enrichir_lot_avec_assets(api_key: str, lot_json: Dict[str, Any]) -> Dict[str, Any]:
    enriched = json.loads(json.dumps(lot_json))  # deepcopy lite
    for client in enriched.get("lot", {}).get("clients", []):
        item_id = int(client["id_monday"])
        resolved = extract_assets_for_client(api_key, item_id, client["structure"])
        all_ids: List[int] = []
        for sub in resolved:
            for f in sub["files"]:
                for a in f["assets"]:
                    all_ids.append(a["asset_id"])
        urls_map = get_assets_public_urls_map(api_key, list(sorted(set(all_ids))))
        for sub in resolved:
            for f in sub["files"]:
                for a in f["assets"]:
                    a["public_url"] = urls_map.get(a["asset_id"])
        client["structure"] = resolved
    return enriched

# ====================== Google Drive (strict) ======================
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

def get_drive_service(creds_path: str = CREDENTIALS_PATH, token_path: str = TOKEN_PATH):
    creds = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception:
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError("credentials.json manquant.")
            with open(creds_path, "r", encoding="utf-8") as f:
                client_config = json.load(f)
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(token_path, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)

def _escape_for_q(s: str) -> str:
    return s.replace("'", r"\'")

def find_or_create_folder_strict(service, name: str, parent_id: str) -> str:
    def _list_existing():
        q = (
            "mimeType='application/vnd.google-apps.folder' "
            "and trashed=false "
            f"and name='{_escape_for_q(name)}' "
            f"and '{parent_id}' in parents"
        )
        resp = service.files().list(
            q=q,
            spaces="drive",
            fields="files(id,name,createdTime)",
            pageSize=100,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            corpora="allDrives",
        ).execute()
        items = resp.get("files", [])
        if items:
            items.sort(key=lambda x: x.get("createdTime",""))
        return items

    for _ in range(2):
        items = _list_existing()
        if items:
            return items[0]["id"]
        time.sleep(0.3)

    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    created = service.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    new_id = created["id"]

    items = _list_existing()
    if items:
        return items[0]["id"]
    return new_id

def _infer_mime_from_name_or_header(filename: str, content_type: Optional[str]) -> str:
    if content_type: return content_type
    fname = (filename or "").lower()
    if fname.endswith(".pdf"):  return "application/pdf"
    if fname.endswith(".jpg"):  return "image/jpeg"
    if fname.endswith(".jpeg"): return "image/jpeg"
    if fname.endswith(".png"):  return "image/png"
    if fname.endswith(".xlsx"): return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if fname.endswith(".xls"):  return "application/vnd.ms-excel"
    if fname.endswith(".docx"): return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if fname.endswith(".doc"):  return "application/msword"
    if fname.endswith(".txt"):  return "text/plain"
    return "application/octet-stream"

def upload_bytes_file(service, parent_id: str, file_name: str, content: bytes, content_type: Optional[str]) -> str:
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=_infer_mime_from_name_or_header(file_name, content_type), resumable=True)
    body = {"name": file_name, "parents": [parent_id]}
    for attempt in range(3):
        try:
            created = service.files().create(
                body=body, media_body=media, fields="id,webViewLink", supportsAllDrives=True
            ).execute()
            return created["id"]
        except Exception:
            if attempt == 2: raise
            time.sleep(1.2 * (attempt + 1))

def download_file_from_public_url(url: Optional[str]) -> Tuple[bytes, Optional[str]]:
    if not url: return b"", None
    r = requests.get(url, stream=True, allow_redirects=True, timeout=60)
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type")

def _sanitize_drive_name(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r'[\\/:*?"<>|]', '-', name)
    name = re.sub(r'\s+', ' ', name)
    return name

def _ext_from_name_or_ctype(file_name: str, content_type: Optional[str]) -> str:
    name = (file_name or "").lower()
    known = ('.pdf', '.jpg', '.jpeg', '.png', '.xlsx', '.xls', '.docx', '.doc', '.txt')
    for k in known:
        if name.endswith(k): return k
    if content_type:
        ct = content_type.lower()
        mapping = {
            'application/pdf': '.pdf',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.ms-excel': '.xls',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/msword': '.doc',
            'text/plain': '.txt',
        }
        if ct in mapping: return mapping[ct]
    return '.bin'

def _compute_next_start_e_id(service, lot_folder_id: str) -> int:
    q = f"'{lot_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    page_token = None
    max_id = 0
    pattern = re.compile(r"^ACT_(\d+)_", re.IGNORECASE)
    while True:
        resp = service.files().list(
            q=q,
            spaces="drive",
            fields="nextPageToken, files(id, name, createdTime)",
            pageSize=1000,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            corpora="allDrives",
            pageToken=page_token
        ).execute()
        for it in resp.get("files", []):
            m = pattern.match(it.get("name", ""))
            if m:
                try:
                    val = int(m.group(1))
                    if val > max_id:
                        max_id = val
                except ValueError:
                    pass
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return max_id + 1 if max_id > 0 else 1

# ====================== Drive upload ======================
def create_lot_on_drive_with_uploads(
    lot_json: Dict[str, Any],
    parent_id: Optional[str] = None,
    lot_folder_id: Optional[str] = None
) -> Dict[str, Any]:
    if not DO_CREATE_DRIVE:
        return {"lotId": None, "clients": {}}
    if not MONDAY_API_KEY:
        raise RuntimeError("MONDAY_API_KEY manquant: impossible de télécharger les fichiers Monday.")
    service = get_drive_service()
    lot = lot_json["lot"]
    lf_id = lot_folder_id or find_or_create_folder_strict(service, lot["nom"], parent_id)
    out = {"lotId": lf_id, "clients": {}}
    for client in lot.get("clients", []):
        client_folder_id = find_or_create_folder_strict(service, client["dossier_principal"], lf_id)
        out["clients"][client["dossier_principal"]] = {"folderId": client_folder_id, "subfolders": {}}
        for sub in client.get("structure", []):
            sub_id = find_or_create_folder_strict(service, sub["nom"], client_folder_id)
            out["clients"][client["dossier_principal"]]["subfolders"][sub["nom"]] = {"id": sub_id, "uploads": []}
            for f in sub.get("files", []):
                assets = f.get("assets", [])
                multi = len(assets) > 1
                base_name = _sanitize_drive_name(f.get("nom") or "FICHIER")
                if SKIP_EXCEL_UPLOAD and "excel" in _norm(f.get("nom", "")):
                    continue
                for idx, a in enumerate(assets, start=1):
                    url = a.get("public_url")
                    orig_name = a.get("name") or base_name
                    try:
                        content, ctype = download_file_from_public_url(url)
                        if not content:
                            continue
                        ext = _ext_from_name_or_ctype(orig_name, ctype)
                        suffix = f"_{idx}" if multi and idx > 1 else ""
                        final_name = f"{base_name}{suffix}{ext}"
                        fid = upload_bytes_file(service, sub_id, final_name, content, ctype)
                        out["clients"][client["dossier_principal"]]["subfolders"][sub["nom"]]["uploads"].append(
                            {"name": final_name, "fileId": fid}
                        )
                    except Exception as e:
                        out["clients"][client["dossier_principal"]]["subfolders"][sub["nom"]]["uploads"].append(
                            {"name": f"{base_name}{('_' + str(idx)) if multi and idx > 1 else ''}", "error": str(e)}
                        )
    return out

# ====================== Monday mutations ======================
def change_status_simple(api_token: str, board_id: int, item_id: int, column_id: str, value: str, create_labels_if_missing: bool = False):
    query = """
    mutation ($boardId: ID!, $itemId: ID!, $columnId: String!, $value: String, $create: Boolean) {
      change_simple_column_value(
        board_id: $boardId,
        item_id: $itemId,
        column_id: $columnId,
        value: $value,
        create_labels_if_missing: $create
      ) { id }
    }
    """
    variables = {"boardId": board_id, "itemId": item_id, "columnId": column_id, "value": value, "create": create_labels_if_missing}
    headers = {"Authorization": api_token, "Content-Type": "application/json"}
    resp = requests.post(MONDAY_API_URL, headers=headers, json={"query": query, "variables": variables}, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]["change_simple_column_value"]["id"]

def update_text_simple(api_token: str, board_id: int, item_id: int, column_id: str, text: str):
    query = """
    mutation ($boardId: ID!, $itemId: ID!, $columnId: String!, $value: String) {
      change_simple_column_value(
        board_id: $boardId,
        item_id: $itemId,
        column_id: $columnId,
        value: $value
      ) { id }
    }
    """
    variables = {"boardId": board_id, "itemId": item_id, "columnId": column_id, "value": text}
    headers = {"Authorization": api_token, "Content-Type": "application/json"}
    r = requests.post(MONDAY_API_URL, headers=headers, json={"query": query, "variables": variables}, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]["change_simple_column_value"]["id"]

def count_success_uploads_for_client(outcome: dict, dossier_principal: str) -> tuple[int, int]:
    cblock = (outcome.get("clients", {}) or {}).get(dossier_principal, {})
    subs = cblock.get("subfolders", {}) or {}
    total = 0
    success = 0
    for subinfo in subs.values():
        for up in subinfo.get("uploads", []) or []:
            total += 1
            if "fileId" in up:
                success += 1
    return success, total

# ====================== Public function (single item) ======================
def deposit_single_item(
    item_id: int,
    lot_folder_name: str,
    root_parent_id: str,
    start_e_id: Optional[int] = None,   # None => auto-increment
    update_status: bool = True,
    auto_increment: bool = True
) -> Dict[str, Any]:
    """
    Deposit ONE client folder into Drive:
      root_parent_id / lot_folder_name / ACT_{id}_{CLIENT} + sub-structure E{id}
    Uses dedicated column_ids for each file and configurable matching rules per column.
    """
    if not MONDAY_API_KEY:
        raise RuntimeError("MONDAY_API_KEY introuvable dans l'environnement.")
    client_name = get_item_name(MONDAY_API_KEY, int(item_id))

    service = get_drive_service()
    lot_folder_id = find_or_create_folder_strict(service, lot_folder_name, root_parent_id)

    # Auto-increment ACT_{id}
    if start_e_id is None and auto_increment:
        start_e_id = _compute_next_start_e_id(service, lot_folder_id)
    if start_e_id is None:
        start_e_id = 1

    clients_input: List[Tuple[str, str]] = [(client_name, str(item_id))]
    lot_payload = generer_structure_lot(lot_numero=1, clients=clients_input, start_id=start_e_id)
    lot_payload["lot"]["nom"] = lot_folder_name

    enriched = enrichir_lot_avec_assets(MONDAY_API_KEY, lot_payload)
    outcome = create_lot_on_drive_with_uploads(enriched, parent_id=root_parent_id, lot_folder_id=lot_folder_id)

    # La mise à jour du texte a été désactivée
    
    if update_status:
        for client in enriched["lot"]["clients"]:
            dossier = client["dossier_principal"]
            iid = int(client["id_monday"])
            succ, total = count_success_uploads_for_client(outcome, dossier)
            if succ > 0:
                try:
                    change_status_simple(MONDAY_API_KEY, BOARD_ID, iid, STATUS_COLUMN_ID, STATUS_VALUE, CREATE_LABEL_IF_MISSING)
                except Exception as e:
                    print(f"⚠️ Impossible de mettre à jour le statut pour item {iid}: {e}")
            else:
                print(f"ℹ️ Aucun upload réussi pour item {iid}, statut non modifié.")

    return outcome
