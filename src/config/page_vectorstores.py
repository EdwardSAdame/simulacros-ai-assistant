# src/config/page_vectorstores.py
import os
from urllib.parse import urlparse
from typing import List

# --- ICFES SPECIFIC STORES ---
VSTORE_ICFES_INGLES              = os.getenv("VECTOR_STORE_ICFES_INGLES", "")
VSTORE_ICFES_CIENCIAS_NATURALES  = os.getenv("VECTOR_STORE_ICFES_CIENCIAS_NATURALES", "")
VSTORE_ICFES_MATEMATICAS         = os.getenv("VECTOR_STORE_ICFES_MATEMATICAS", "")
VSTORE_ICFES_SOCIALES_CIUDADANAS = os.getenv("VECTOR_STORE_ICFES_SOCIALES_CIUDADANAS", "")
VSTORE_ICFES_LECTURA_CRITICA     = os.getenv("VECTOR_STORE_ICFES_LECTURA_CRITICA", "")

# --- UNAL SPECIFIC STORES ---
VSTORE_UNAL_ANALISIS_IMAGEN      = os.getenv("VECTOR_STORE_UNAL_ANALISIS_IMAGEN", "")
VSTORE_UNAL_MATEMATICAS          = os.getenv("VECTOR_STORE_UNAL_MATEMATICAS", "")
VSTORE_UNAL_TEMATICA_COMUN       = os.getenv("VECTOR_STORE_UNAL_TEMATICA_COMUN", "")
VSTORE_UNAL_CIENCIAS_SOCIALES    = os.getenv("VECTOR_STORE_UNAL_CIENCIAS_SOCIALES", "")
VSTORE_UNAL_CIENCIAS_NATURALES   = os.getenv("VECTOR_STORE_UNAL_CIENCIAS_NATURALES", "")

# Mapping ONLY for specific simulation zones
_PAGE_MAP = {
    # ICFES SPECIFIC SIMULATION ZONES
    "/simulacro-icfes/ingles":                VSTORE_ICFES_INGLES,
    "/simulacro-icfes/ciencias-naturales":    VSTORE_ICFES_CIENCIAS_NATURALES,
    "/simulacro-icfes/matematicas":           VSTORE_ICFES_MATEMATICAS,
    "/simulacro-icfes/sociales-y-cuidadanas": VSTORE_ICFES_SOCIALES_CIUDADANAS,
    "/simulacro-icfes/lectura-critica":       VSTORE_ICFES_LECTURA_CRITICA,

    # UNAL SPECIFIC SIMULATION ZONES
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

def get_stores_for_page(page: str | None) -> List[str]:
    path = _normalize_path(page)
    
    # 1. Try Exact Match
    specific = _PAGE_MAP.get(path)
    
    # 2. Try Prefix Match (Deep linking)
    # This allows /simulacro-icfes/matematicas/pregunta-1 to still catch the vector store
    if not specific:
        for prefix, sid in _PAGE_MAP.items():
            if sid and (path == prefix or path.startswith(prefix + "/")):
                specific = sid
                break

    stores: List[str] = []
    
    # Only append if we found a specific store for this simulation zone
    if specific:
        stores.append(specific)

    # NOTE: Global/General stores logic has been removed as requested.
    
    return stores