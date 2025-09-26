# src/config/page_vectorstores.py
"""
Page → Vector Store resolver.

- Accepts full URLs or plain paths.
- If the page matches a known component, return [specific_store, global].
- Otherwise return [global].
- Env vars must be set in .env (VECTOR_STORE_*).
"""

import os
from urllib.parse import urlparse
from typing import List

# Single global store
VSTORE_GLOBAL = os.getenv("VECTOR_STORE_GLOBAL", "")

# ICFES
VSTORE_ICFES_INGLES              = os.getenv("VECTOR_STORE_ICFES_INGLES", "")
VSTORE_ICFES_CIENCIAS_NATURALES  = os.getenv("VECTOR_STORE_ICFES_CIENCIAS_NATURALES", "")
VSTORE_ICFES_MATEMATICAS         = os.getenv("VECTOR_STORE_ICFES_MATEMATICAS", "")
VSTORE_ICFES_SOCIALES_CIUDADANAS = os.getenv("VECTOR_STORE_ICFES_SOCIALES_CIUDADANAS", "")
VSTORE_ICFES_LECTURA_CRITICA     = os.getenv("VECTOR_STORE_ICFES_LECTURA_CRITICA", "")

# UNAL
VSTORE_UNAL_ANALISIS_IMAGEN      = os.getenv("VECTOR_STORE_UNAL_ANALISIS_IMAGEN", "")
VSTORE_UNAL_MATEMATICAS          = os.getenv("VECTOR_STORE_UNAL_MATEMATICAS", "")
VSTORE_UNAL_TEMATICA_COMUN       = os.getenv("VECTOR_STORE_UNAL_TEMATICA_COMUN", "")
VSTORE_UNAL_CIENCIAS_SOCIALES    = os.getenv("VECTOR_STORE_UNAL_CIENCIAS_SOCIALES", "")
VSTORE_UNAL_CIENCIAS_NATURALES   = os.getenv("VECTOR_STORE_UNAL_CIENCIAS_NATURALES", "")

# Path → specific store
_PAGE_MAP = {
    # ICFES
    "/simulacro-icfes/ingles":                VSTORE_ICFES_INGLES,
    "/simulacro-icfes/ciencias-naturales":    VSTORE_ICFES_CIENCIAS_NATURALES,
    "/simulacro-icfes/matematicas":           VSTORE_ICFES_MATEMATICAS,
    "/simulacro-icfes/sociales-y-cuidadanas": VSTORE_ICFES_SOCIALES_CIUDADANAS,
    "/simulacro-icfes/lectura-critica":       VSTORE_ICFES_LECTURA_CRITICA,

    # UNAL
    "/simulacro-unal/analisis-de-imagen":     VSTORE_UNAL_ANALISIS_IMAGEN,
    "/simulacro-unal/matematicas":            VSTORE_UNAL_MATEMATICAS,
    "/simulacro-unal/tematica-comun":         VSTORE_UNAL_TEMATICA_COMUN,
    "/simulacro-unal/ciencias-sociales":      VSTORE_UNAL_CIENCIAS_SOCIALES,
    "/simulacro-unal/ciencias-naturales":     VSTORE_UNAL_CIENCIAS_NATURALES,
}


def _normalize_path(page: str | None) -> str:
    if not page:
        return "/"
    s = page.strip()
    parsed = urlparse(s)
    path = parsed.path or s
    return path.lower()


def get_stores_for_page(page: str | None) -> List[str]:
    """
    Returns vector_store_ids ordered by priority.
    - Known component: [specific, global]
    - Unknown page:    [global]
    Ensures at least one id if VECTOR_STORE_GLOBAL is set.
    """
    path = _normalize_path(page)

    specific = _PAGE_MAP.get(path)
    # prefix match for deeper routes
    if not specific:
        for prefix, sid in _PAGE_MAP.items():
            if sid and (path == prefix or path.startswith(prefix + "/")):
                specific = sid
                break

    stores: List[str] = []
    if specific:
        stores.append(specific)

    if VSTORE_GLOBAL and VSTORE_GLOBAL not in stores:
        stores.append(VSTORE_GLOBAL)

    return stores
