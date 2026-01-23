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

# --- 3. Imports ---
from src.assistant.assistant_client import send_message_to_assistant
from src.config.model_config import get_model_config
from src.utils.time_utils import get_current_time_info

# --- 4. Logging ---
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def _build_conversation_history(user_input: str) -> List[Dict[str, Any]]:
    return [{"role": "user", "content": [{"type": "input_text", "text": user_input}]}]

def _get_runtime_context():
    return "test-user-pdf", "simulacro-unal/test-pdf", "PDF Tester", "pdf@example.com"

def main():
    print("\n===============================================")
    print("Invicto AI PDF Analysis Test")
    print("===============================================\n")

    # Default URL for quick testing
    default_pdf = "https://cdn.openai.com/API/docs/images/gpt-4-turbo-vision-system-card.pdf"

    while True:
        print("\n-----------------------------------------------")
        mode_input = input("Select Mode [A]lpha (Logic) / [O]mega (Standard) / [E]xit: ").strip().lower()

        if mode_input in ["exit", "e"]:
            print("Session ended.\n")
            break
        
        mode = "omega"
        if mode_input in ["a", "alpha"]: mode = "alpha"
        elif mode_input in ["o", "omega"]: mode = "omega"
        else: print("Invalid input. Defaulting to Omega.")

        # Verify what parameters are active
        cfg = get_model_config(mode)
        
        print(f"\nActive Profile: {mode.upper()}")
        print(f"   Model: {cfg.model}")

        # --- ASK FOR PDF URL ---
        print(f"\nEnter PDF URL (Press Enter for OpenAI System Card default)")
        pdf_input = input("   URL: ").strip()
        
        target_pdf_url = pdf_input if pdf_input else default_pdf
        print(f"   Using PDF: {target_pdf_url}")

        while True:
            user_input = input(f"\nYou ({mode.upper()}): ").strip()
            
            if user_input.lower() in ["exit", "e", "back"]: break 
            if not user_input: continue

            user_id, page, name, email = _get_runtime_context()
            history = _build_conversation_history(user_input)
            
            print(f"\nThinking with {cfg.model} + PDF Analysis...")
            start_time = time.time()
            
            try:
                # CALL THE CLIENT WITH PDF
                ai_reply, generated_assets, sources = send_message_to_assistant(
                    conversation_input=history,
                    user_id=user_id,
                    page=page,
                    name=name,
                    email=email,
                    mode=mode,
                    pdf_urls=[target_pdf_url]
                )
                latency = time.time() - start_time
                
                print(f"\nRoma AI ({latency:.2f}s):\n{ai_reply}\n")
                
                if generated_assets:
                    print(f"   Generated Assets: {generated_assets}")
                if sources:
                    print(f"   Sources: {sources}")
                
            except Exception as e:
                print(f"\nERROR ({mode.upper()}): {e}\n")

if __name__ == "__main__":
    main()