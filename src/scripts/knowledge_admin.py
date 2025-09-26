# src/scripts/knowledge_admin.py
#!/usr/bin/env python3
"""
CLI to create vector stores and upload knowledge files for the web chatbot.

Usage:
  # Bootstrap all stores from 'knowledge/' and upload all supported files
  python src/scripts/knowledge_admin.py bootstrap --root src/knowledge

  # List vector stores
  python src/scripts/knowledge_admin.py list-stores

  # Upload a single file to a specific store name
  python src/scripts/knowledge_admin.py upload --store "icfes-matematicas" --file src/knowledge/icfes/matematicas.json

Notes:
- Requires OPENAI_API_KEY in .env at project root
- Store naming:
    general               -> "general"
    icfes/<component>     -> "icfes-<component>"
    unal/<component>      -> "unal-<component>"
- Prints a block to paste into .env with VECTOR_STORE_* IDs.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from openai import OpenAI

# ---------- setup ----------
# climb two levels up (src/scripts → project root)
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

# Folder → ENV key mapping (normalized with underscores)
ENV_KEYS = {
    "general": "VECTOR_STORE_GLOBAL",
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
    rel = path.as_posix().split("knowledge/")[-1].strip("/")
    if rel == "general":
        return "general", ENV_KEYS["general"]

    parts = rel.split("/")
    if len(parts) == 2 and parts[0] in ("icfes", "unal"):
        # normalize env key by replacing '-' with '_'
        folder_key = f"{parts[0]}/{parts[1].replace('-', '_')}"
        env_key = ENV_KEYS.get(folder_key)
        if env_key:
            # store name uses kebab-case
            store_name = f"{parts[0]}-{parts[1].replace('_', '-')}"
            return store_name, env_key

    safe = rel.replace("/", "-").replace("_", "-")
    return safe, f"VECTOR_STORE_{safe.upper().replace('-', '_')}"


def _collect_files(dirpath: Path) -> List[Path]:
    files = []
    for p in dirpath.rglob("*"):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            files.append(p)
    return files


def _ensure_store(name: str) -> str:
    """
    Create a vector store if needed. Return its id.
    Reuse by name if it already exists.
    """
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
def cmd_list_stores(_args):
    stores = client.vector_stores.list(limit=100)
    for vs in stores.data:
        print(f"{vs.id}\t{vs.name}")


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
    print(f"file_id: {fid}")


def cmd_bootstrap(args):
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Knowledge root not found: {root}", file=sys.stderr)
        sys.exit(1)

    env_out: Dict[str, str] = {}

    # traverse: knowledge/general, knowledge/icfes/*, knowledge/unal/*
    for sub in sorted([p for p in root.iterdir() if p.is_dir()]):
        nested = [p for p in sub.iterdir() if p.is_dir()]
        targets = nested or [sub]
        for folder in sorted(targets):
            files = _collect_files(folder)
            if not files:
                continue
            store_name, env_key = _store_name_for(folder)
            store_id = _ensure_store(store_name)

            for fp in files:
                fid = _upload_file(fp)
                _attach_file(store_id, fid)
                print(f"[{store_name}] + {fp.relative_to(root)} (file_id={fid})")

            env_out[env_key] = store_id

    # provide a default if you rely on it
    if "VECTOR_STORE_DEFAULT" not in env_out and "VECTOR_STORE_GLOBAL" in env_out:
        env_out["VECTOR_STORE_DEFAULT"] = env_out["VECTOR_STORE_GLOBAL"]

    print("\n# ---- Paste into .env ----")
    for k, v in sorted(env_out.items()):
        print(f"{k}={v}")


# ----------------- CLI -----------------
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("list-stores").set_defaults(func=cmd_list_stores)

    up = sub.add_parser("upload")
    up.add_argument("--store", required=True, help="Target store name (e.g., icfes-matematicas)")
    up.add_argument("--file", required=True, help="Path to file")
    up.set_defaults(func=cmd_upload)

    boot = sub.add_parser("bootstrap")
    boot.add_argument("--root", default="src/knowledge", help="Knowledge root folder")
    boot.set_defaults(func=cmd_bootstrap)

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
