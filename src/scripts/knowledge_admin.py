#!/usr/bin/env python3
"""
CLI to create/cleanup vector stores and upload knowledge files.
UPDATED: Traverses exam directories, creates ONE vector store per exam folder, 
and uploads all split JSON questions inside it. Supports single-exam execution.
Includes a safe cleanup command to target specific exam types (e.g., ICFES).
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

def cmd_cleanup(args):
    """Deletes vector stores containing a specific target string to avoid wiping everything."""
    target = args.target.upper()
    print(f"WARNING: This will delete vector stores containing '{target}' in their name.")
    confirm = input("Are you sure? (type 'yes' to confirm): ")
    if confirm != "yes":
        print("Aborted.")
        return

    stores = client.vector_stores.list(limit=100)
    count = 0
    for vs in stores.data:
        vs_name = getattr(vs, "name", "")
        if target in vs_name.upper():
            print(f"Deleting store: {vs_name} ({vs.id})...")
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
    target_exam = args.exam

    if not root.exists():
        print(f"Knowledge root not found: {root}", file=sys.stderr)
        sys.exit(1)

    env_out: Dict[str, str] = {}
    cat_path = root / "icfes"
    
    if not cat_path.exists():
        print("No 'icfes' directory found in knowledge root.")
        return

    # Iterate through subject folders (e.g., matematicas, lectura_critica)
    for subject_dir in cat_path.iterdir():
        if not subject_dir.is_dir() or subject_dir.name == "general":
            continue

        # Iterate through exam folders (e.g., math_vol_01, lecture_vol_01)
        for exam_dir in subject_dir.iterdir():
            if not exam_dir.is_dir():
                continue

            exam_name = exam_dir.name

            # If the user passed --exam, skip any folder that does not match
            if target_exam and target_exam.lower() != exam_name.lower():
                continue

            json_files = _collect_files(exam_dir)
            if not json_files:
                print(f"Skipping empty exam folder: {exam_name}")
                continue

            store_name = f"ExamStore_ICFES_{exam_name}"
            env_key = f"VECTOR_STORE_ICFES_{exam_name.upper()}"

            print(f"\nProcessing Exam Directory: [{exam_name}] -> Store: [{store_name}]")
            print(f"Found {len(json_files)} questions. Uploading...")

            store_id = _ensure_store(store_name)
            env_out[env_key] = store_id

            for fp in json_files:
                fid = _upload_file(fp)
                _attach_file(store_id, fid)
                print(f"  + Attached {fp.name}")

    if not env_out:
        print("\nNo stores were created or updated.")
        return

    print("\n# ---- Paste into your AWS Lambda Environment Variables (.env) ----")
    for k, v in sorted(env_out.items()):
        print(f"{k}={v}")


# ----------------- CLI -----------------
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("list-stores").set_defaults(func=cmd_list_stores)
    
    clean = sub.add_parser("cleanup")
    clean.add_argument("--target", default="ICFES", help="Delete only stores containing this string in their name")
    clean.set_defaults(func=cmd_cleanup)

    up = sub.add_parser("upload")
    up.add_argument("--store", required=True)
    up.add_argument("--file", required=True)
    up.set_defaults(func=cmd_upload)

    boot = sub.add_parser("bootstrap")
    boot.add_argument("--root", default="src/knowledge")
    boot.add_argument("--exam", default=None, help="Process only a specific exam folder (e.g., math_vol_01)")
    boot.set_defaults(func=cmd_bootstrap)

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()