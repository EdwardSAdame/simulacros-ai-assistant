import os
import logging
from urllib.parse import urlparse
from typing import List
from src.storage.vector_store_table import VectorStoreTable

logger = logging.getLogger(__name__)

# --- UNAL SPECIFIC STORES (Legacy - Kept for backward compatibility) ---
VSTORE_UNAL_ANALISIS_IMAGEN      = os.getenv("VECTOR_STORE_UNAL_ANALISIS_IMAGEN", "")
VSTORE_UNAL_MATEMATICAS          = os.getenv("VECTOR_STORE_UNAL_MATEMATICAS", "")
VSTORE_UNAL_TEMATICA_COMUN       = os.getenv("VECTOR_STORE_UNAL_TEMATICA_COMUN", "")
VSTORE_UNAL_CIENCIAS_SOCIALES    = os.getenv("VECTOR_STORE_UNAL_CIENCIAS_SOCIALES", "")
VSTORE_UNAL_CIENCIAS_NATURALES   = os.getenv("VECTOR_STORE_UNAL_CIENCIAS_NATURALES", "")

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

    # 1. NEW LOGIC: DynamoDB Registry Lookup
    if exam_id:
        try:
            parsed_url = urlparse(exam_id)
            path = parsed_url.path
            
            # Extract the relative path without leading slash and extension
            # Example: /icfes/math/2025_2_session1/math_vol_01.json -> icfes/math/2025_2_session1/math_vol_01
            clean_exam_id = path.lstrip('/').replace(".json", "").strip()
            
            if clean_exam_id:
                db = VectorStoreTable()
                store_id = db.get_vector_store_id(clean_exam_id)
                
                if store_id:
                    stores.append(store_id)
                    logger.info(f"Successfully resolved vector store for {clean_exam_id}")
                    return stores 
                else:
                    logger.warning(f"No vector store found in DynamoDB for ExamId: {clean_exam_id}")
                    
        except Exception as e:
            logger.error(f"Error parsing exam_id '{exam_id}' for vector store resolution: {e}")

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

    return stores