import sys
import os
import time
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# --- 1. Setup Path to find 'src' ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 2. Force Load Environment Variables ---
load_dotenv(override=True)

from src.assistant.assistant_client import send_message_to_assistant
from src.config.model_config import get_model_config
from src.config.web_search_config import get_search_filters
from src.config.settings import settings

# Configure simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    print("\n========================================")
    print("🌍  INTERACTIVE WEB SEARCH (Deep Research)")
    print("========================================")

    # 1. Load Configuration
    cfg = get_model_config("omega") 
    search_model = cfg.search_model
    
    # Audit Settings
    print(f"⚙️  Active Model:      {search_model}")
    print(f"🔒  AWS Strict Mode:   {settings.WEB_SEARCH_STRICT_MODE}")
    if settings.WEB_SEARCH_STRICT_MODE:
        print("    (Search restricted to specific domains. Set WEB_SEARCH_STRICT_MODE=false for Open Web)")
    else:
        print("    (Search is OPEN to the entire internet)")
    
    print("========================================\n")

    # 2. Main Loop
    while True:
        print("\n" + "-"*50)
        query = input("🔎  Enter Query (or 'exit'): ").strip()
        
        if query.lower() in ['exit', 'quit', 'e']:
            print("👋  Exiting...")
            break
        
        if not query:
            continue

        # 🟢 AUTO-CONTEXT LOGIC (Simulating the Router)
        # We assume 'General' unless keywords are found
        context_key = "General"
        if "icfes" in query.lower():
            context_key = "ICFES"
        elif "unal" in query.lower() or "nacional" in query.lower():
            context_key = "UNAL"
        elif "andes" in query.lower() or "beca" in query.lower():
            context_key = "UNIANDES"

        # 3. Get Filters
        filters = get_search_filters(context_key)

        # 4. Display Active Logic
        print(f"\n📋  Context: {context_key}")
        if filters and "allowed_domains" in filters:
            print(f"    -> STRICT MODE (White-list Active)")
            print(f"    -> Allowed: {filters['allowed_domains']}")
        elif filters and filters.get("scope") == "open_web":
            print(f"    -> OPEN WEB MODE (No Restrictions)")
        else:
            print(f"    -> STANDARD CHAT (No Search Tool injected)")

        # 5. Execute API Call
        print(f"\n🧠  Thinking... (Model: {search_model})")
        start_time = time.time()

        try:
            conversation_input = [{"role": "user", "content": [{"type": "input_text", "text": query}]}]
            
            response_text, assets = send_message_to_assistant(
                conversation_input=conversation_input,
                user_id="interactive-user",
                page="test-cli",
                web_search_config=filters,
                model_override=search_model 
            )
            
            latency = time.time() - start_time
            
            # 6. Print Result
            print(f"\n🤖  Response ({latency:.2f}s):\n")
            print(response_text)
            print("-" * 50)
            
            if "Fuentes Consultadas" in response_text:
                print("✅  Sources found.")
            else:
                print("ℹ️  No sources cited.")

        except Exception as e:
            print(f"\n❌  ERROR: {e}")

if __name__ == '__main__':
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY not found in .env")
    else:
        main()