# tests/test_assistant.py
import sys
import os
import time
import logging
from typing import List, Dict, Any

# --- 1. Setup Path to find 'src' ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 2. Imports ---
from src.assistant.assistant_client import send_message_to_assistant
from src.config.model_config import get_model_config  # <--- 🟢 Import config loader
from src.utils.time_utils import get_current_time_info

# --- 3. Enable Logging to Console ---
# This allows you to see "Assistant Client: Detected reasoning model..." warnings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def _build_conversation_history(user_input: str) -> List[Dict[str, Any]]:
    """Builds the simple user turn for the API."""
    return [
        {"role": "user", "content": [{"type": "input_text", "text": user_input}]},
    ]

def _get_runtime_context():
    """Mock context data."""
    user_id = "test-user-worker"
    page = "simulacro-unal/ciencias-naturales"
    name = "Test User"
    email = "test@example.com"
    return user_id, page, name, email

def main():
    print("\n===============================================")
    print("🔹 Invicto AI Worker Test (Alpha vs. Omega)")
    print("===============================================\n")

    # 🔹 1. Loop: Mode Selection
    while True:
        print("\n-----------------------------------------------")
        mode_input = input("⚙️  Select Mode [A]lpha (Smart) / [O]mega (Fast) / [E]xit: ").strip().lower()

        if mode_input in ["exit", "e"]:
            print("👋 Session ended.\n")
            break
        
        mode = "omega" # Default
        if mode_input in ["a", "alpha"]:
            mode = "alpha"
        elif mode_input in ["o", "omega"]:
            mode = "omega"
        else:
            print("❌ Invalid input. Defaulting to Omega.")

        # 🔍 INSPECTION: Verify what the app actually loaded
        cfg = get_model_config(mode)
        print(f"\n✅ Active Profile: {mode.upper()}")
        print(f"   Model: {cfg.model}")
        # print(f"   Max Tokens: {cfg.max_tokens}") <--- DELETED (Variable no longer exists)
        print(f"   Temp:  {cfg.temperature}")
        print(f"   Top P: {cfg.top_p}")

        # 🔹 2. Loop: Chat
        while True:
            user_input = input(f"\n👤 You ({mode.upper()}): ").strip()
            
            if user_input.lower() in ["exit", "e", "back"]:
                break # Go back to mode selection
            if not user_input:
                continue

            # Context & History
            user_id, page, name, email = _get_runtime_context()
            conversation_history = _build_conversation_history(user_input)
            
            print(f"\n🧠 Thinking with {cfg.model}...")
            start_time = time.time()
            
            try:
                # 🚀 CALL THE CLIENT
                ai_reply = send_message_to_assistant(
                    conversation_input=conversation_history,
                    user_id=user_id,
                    page=page,
                    name=name,
                    email=email,
                    mode=mode # <--- Passing the mode
                )
                end_time = time.time()
                latency = end_time - start_time
                
                print(f"\n🤖 Roma AI ({latency:.2f}s):\n{ai_reply}\n")
                
            except Exception as e:
                print(f"\n❌ ERROR ({mode.upper()}): {e}\n")

if __name__ == "__main__":
    main()