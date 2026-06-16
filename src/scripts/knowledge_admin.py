#!/usr/bin/env python3
"""
CLI to create/cleanup vector stores and upload knowledge files.
UPDATED: Creates a unique Vector Store for EVERY SINGLE FILE in ICFES, 
skipping 'general' and applying explicit ICFES prefix markers.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List

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

SUPPORTED_EXTS = {".json"}

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
    all_files = []
    
    cat_path = root / "icfes"
    if cat_path.exists():
        for sub_dir in cat_path.iterdir():
            if sub_dir.is_dir():
                if sub_dir.name == "general":
                    print("Skipping 'general' folder...")
                    continue
                all_files.extend(_collect_files(sub_dir))

    if not all_files:
        print("No JSON files found in valid icfes directories.")
        return

    print(f"Found {len(all_files)} files. Creating individual Vector Stores...")

    for fp in all_files:
        file_stem = fp.stem  # e.g., math_vol_02
        
        # Prefixed named architecture to allow clean domain separation
        store_name = f"ExamStore_ICFES_{file_stem}"
        env_key = f"VECTOR_STORE_ICFES_{file_stem.upper()}"

        print(f"\nProcessing File: [{fp.name}] -> Store: [{store_name}]")
        
        store_id = _ensure_store(store_name)
        fid = _upload_file(fp)
        _attach_file(store_id, fid)
        
        env_out[env_key] = store_id
        print(f"  + Uploaded and attached successfully.")

    print("\n# ---- Paste into your AWS Lambda Environment Variables (.env) ----")
    for k, v in sorted(env_out.items()):
        print(f"{k}={v}")


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