# src/scripts/knowledge_admin.py
#!/usr/bin/env python3
"""
CLI to create/cleanup vector stores and upload knowledge files.

Usage:
  # 1. DELETE ALL existing stores (Start Fresh)
  python src/scripts/knowledge_admin.py cleanup

  # 2. Bootstrap all stores from 'knowledge/' and upload files
  python src/scripts/knowledge_admin.py bootstrap --root src/knowledge

  # 3. List vector stores to verify
  python src/scripts/knowledge_admin.py list-stores

Notes:
- Requires OPENAI_API_KEY in .env
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from openai import OpenAI

# ---------- setup ----------
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=True)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not set in .env", file=sys.stderr)
    sys.exit(1)

client = OpenAI(api_key=api_key)

SUPPORTED_EXTS = {
    ".json", ".pdf", ".md", ".txt", ".docx", ".pptx", ".html",
}

# 🟢 UPDATED: Removed 'general', 'icfes/general', and 'unal/general'
ENV_KEYS = {
    # ICFES
    "icfes/ingles": "VECTOR_STORE_ICFES_INGLES",
    "icfes/ciencias_naturales": "VECTOR_STORE_ICFES_CIENCIAS_NATURALES",
    "icfes/matematicas": "VECTOR_STORE_ICFES_MATEMATICAS",
    "icfes/sociales_ciudadanas": "VECTOR_STORE_ICFES_SOCIALES_CIUDADANAS",
    "icfes/lectura_critica": "VECTOR_STORE_ICFES_LECTURA_CRITICA",
    
    # UNAL
    "unal/analisis_imagen": "VECTOR_STORE_UNAL_ANALISIS_IMAGEN",
    "unal/matematicas": "VECTOR_STORE_UNAL_MATEMATICAS",
    "unal/tematica_comun": "VECTOR_STORE_UNAL_TEMATICA_COMUN",
    "unal/ciencias_sociales": "VECTOR_STORE_UNAL_CIENCIAS_SOCIALES",
    "unal/ciencias_naturales": "VECTOR_STORE_UNAL_CIENCIAS_NATURALES",
}


def _store_name_for(path: Path) -> Tuple[str, str]:
    """
    Given a folder under knowledge/, return (store_name, env_key).
    """
    # normalize path relative to knowledge root
    try:
        rel = path.relative_to(path.parent.parent).as_posix() # e.g. "icfes/matematicas"
    except ValueError:
        # fallback for top level
        rel = path.name

    # Check explicit map first (handles icfes/matematicas, etc)
    if rel in ENV_KEYS:
        # e.g., "icfes-matematicas"
        store_name = rel.replace("/", "-")
        return store_name, ENV_KEYS[rel]

    print(f"⚠️ Warning: No mapping found for folder '{rel}', skipping...")
    return None, None


def _collect_files(dirpath: Path) -> List[Path]:
    files = []
    for p in dirpath.rglob("*"):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            files.append(p)
    return files


def _ensure_store(name: str) -> str:
    stores = client.vector_stores.list(limit=100)
    for vs in stores.data:
        if getattr(vs, "name", "") == name:
            return vs.id
    vs = client.vector_stores.create(name=name)
    return vs.id


def _upload_file(file_path: Path) -> str:
    with open(file_path, "rb") as fh:
        f = client.files.create(file=fh, purpose="assistants")
    return f.id


def _attach_file(store_id: str, file_id: str) -> None:
    client.vector_stores.files.create(vector_store_id=store_id, file_id=file_id)


# ----------------- commands -----------------

def cmd_cleanup(_args):
    """Deletes all vector stores created by this bot to start fresh."""
    print("WARNING: This will delete ALL vector stores in your OpenAI project.")
    confirm = input("Are you sure? (type 'yes' to confirm): ")
    if confirm != "yes":
        print("Aborted.")
        return

    stores = client.vector_stores.list(limit=100)
    count = 0
    for vs in stores.data:
        # Optional: Filter by name prefix if you share this project
        # if not vs.name.startswith("icfes") and not vs.name.startswith("unal"): continue
        print(f"Deleting store: {vs.name} ({vs.id})...")
        client.vector_stores.delete(vs.id)
        count += 1
    print(f"Done. Deleted {count} stores.")


def cmd_list_stores(_args):
    stores = client.vector_stores.list(limit=100)
    print(f"{'ID':<30} | {'NAME'}")
    print("-" * 50)
    for vs in stores.data:
        print(f"{vs.id:<30} | {vs.name}")


def cmd_upload(args):
    store_name = args.store
    file_path = Path(args.file).resolve()
    if not file_path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    store_id = _ensure_store(store_name)
    fid = _upload_file(file_path)
    _attach_file(store_id, fid)
    print(f"Uploaded {file_path.name} -> {store_name} ({store_id})")


def cmd_bootstrap(args):
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Knowledge root not found: {root}", file=sys.stderr)
        sys.exit(1)

    env_out: Dict[str, str] = {}

    # 1. Sub-folders (icfes/*, unal/*)
    # We now strictly iterate only these folders looking for keys in ENV_KEYS
    for category in ["icfes", "unal"]:
        cat_path = root / category
        if cat_path.exists():
            for sub in cat_path.iterdir():
                if sub.is_dir():
                    _process_folder(sub, root, env_out)

    print("\n# ---- Paste into .env ----")
    for k, v in sorted(env_out.items()):
        print(f"{k}={v}")

def _process_folder(folder_path, root, env_out):
    # Calculate relative path string e.g., "icfes/matematicas"
    rel_path = folder_path.relative_to(root).as_posix()
    
    if rel_path in ENV_KEYS:
        env_key = ENV_KEYS[rel_path]
        store_name = rel_path.replace("/", "-")
    else:
        # Skip obsolete general folders or unknown folders
        return

    files = _collect_files(folder_path)
    if not files:
        return

    print(f"\nProcessing [{store_name}]...")
    store_id = _ensure_store(store_name)
    
    for fp in files:
        fid = _upload_file(fp)
        _attach_file(store_id, fid)
        print(f"  + {fp.name}")

    env_out[env_key] = store_id


# ----------------- CLI -----------------
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("list-stores").set_defaults(func=cmd_list_stores)
    sub.add_parser("cleanup").set_defaults(func=cmd_cleanup)

    up = sub.add_parser("upload")
    up.add_argument("--store", required=True)
    up.add_argument("--file", required=True)
    up.set_defaults(func=cmd_upload)

    boot = sub.add_parser("bootstrap")
    boot.add_argument("--root", default="src/knowledge")
    boot.set_defaults(func=cmd_bootstrap)

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()