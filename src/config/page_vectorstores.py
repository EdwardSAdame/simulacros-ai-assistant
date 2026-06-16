# src/config/page_vectorstores.py
import os
from urllib.parse import urlparse
from typing import List

# --- UNAL SPECIFIC STORES (Legacy - Kept exactly as before) ---
VSTORE_UNAL_ANALISIS_IMAGEN      = os.getenv("VECTOR_STORE_UNAL_ANALISIS_IMAGEN", "")
VSTORE_UNAL_MATEMATICAS          = os.getenv("VECTOR_STORE_UNAL_MATEMATICAS", "")
VSTORE_UNAL_TEMATICA_COMUN       = os.getenv("VECTOR_STORE_UNAL_TEMATICA_COMUN", "")
VSTORE_UNAL_CIENCIAS_SOCIALES    = os.getenv("VECTOR_STORE_UNAL_CIENCIAS_SOCIALES", "")
VSTORE_UNAL_CIENCIAS_NATURALES   = os.getenv("VECTOR_STORE_UNAL_CIENCIAS_NATURALES", "")

# Mapping ONLY for legacy simulation zones (UNAL)
_PAGE_MAP = {
    "/simulacro-unal/analisis-de-imagen":     VSTORE_UNAL_ANALISIS_IMAGEN,
    "/simulacro-unal/matematicas":            VSTORE_UNAL_MATEMATICAS,
    "/simulacro-unal/tematica-comun":         VSTORE_UNAL_TEMATICA_COMUN,
    "/simulacro-unal/ciencias-sociales":      VSTORE_UNAL_CIENCIAS_SOCIALES,
    "/simulacro-unal/ciencias-naturales":     VSTORE_UNAL_CIENCIAS_NATURALES,
}

def _normalize_path(page: str | None) -> str:
    if not page: return "/"
    s = page.strip()
    parsed = urlparse(s)
    path = parsed.path or s
    return path.lower()

def get_stores_for_page(page: str | None, exam_id: str | None = None) -> List[str]:
    stores: List[str] = []

    # 1. NEW LOGIC: Dynamic ICFES Exam Lookup
    # If the frontend sent an examId (e.g., 'math_vol_02.json'), look up its specific Vector Store
    if exam_id:
        # Clean the exam_id (remove .json if present)
        clean_exam_id = exam_id.lower().replace(".json", "").strip()
        
        # Convert to the environment variable format with the ICFES prefix:
        # math_vol_02 -> VECTOR_STORE_ICFES_MATH_VOL_02
        env_var_name = f"VECTOR_STORE_ICFES_{clean_exam_id.upper()}"
        
        # Dynamically fetch the ID from the environment variables
        specific_exam_store = os.getenv(env_var_name, "")
        if specific_exam_store:
            stores.append(specific_exam_store)
            return stores # If we found the specific exam, return immediately!

    # 2. LEGACY LOGIC: UNAL Path Lookup (Fallback)
    path = _normalize_path(page)
    specific = _PAGE_MAP.get(path)
    
    if not specific:
        for prefix, sid in _PAGE_MAP.items():
            if sid and (path == prefix or path.startswith(prefix + "/")):
                specific = sid
                break

    if specific:
        stores.append(specific)

    # NOTE: Global/General stores logic has been removed as requested.
    return stores