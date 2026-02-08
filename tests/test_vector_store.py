# tests/test_vector_store.py
import logging
import sys
import os

# 1. Setup path to import from 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. Import the manager
from src.assistant.vector_store_manager import vector_store_manager

# Configure logging so we can see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_create_vector_store():
    print("\n🚀 --- STARTING VECTOR STORE TEST ---\n")

    # Use a small, public PDF for testing
    test_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    arena_title = "Test Arena Integration"

    print(f"1. Attempting to download and upload file: {test_url}")
    print(f"2. Creating Vector Store for: '{arena_title}'")

    try:
        # Call the function we just wrote
        vs_id = vector_store_manager.create_arena_knowledge_base(
            arena_name=arena_title,
            file_urls=[test_url]
        )

        if vs_id:
            print(f"\n✅ SUCCESS! Vector Store Created Successfully.")
            print(f"🆔 Vector Store ID: {vs_id}")
            print("You can now verify this ID in your OpenAI Dashboard under 'Storage'.")
        else:
            print("\n❌ FAILED. The function returned None.")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    # Ensure OPENAI_API_KEY is available
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY not found in environment variables.")
        print("   Make sure to run: export OPENAI_API_KEY='sk-...' before running this script.")
    else:
        test_create_vector_store()