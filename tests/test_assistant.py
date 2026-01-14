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
logging.basicConfig(level=logging.ERROR) # Keep it quiet except for errors
logger = logging.getLogger(__name__)

def _build_conversation_history(user_input: str) -> List[Dict[str, Any]]:
    return [{"role": "user", "content": [{"type": "input_text", "text": user_input}]}]

def _get_runtime_context():
    return "test-user-worker", "simulacro-unal/ciencias-naturales", "Test User", "test@example.com"

def main():
    print("\n===============================================")
    print("🔹 Invicto AI Assistant Test (Alpha vs. Omega)")
    print("===============================================\n")

    while True:
        print("\n-----------------------------------------------")
        mode_input = input("⚙️  Select Mode [A]lpha (Logic) / [O]mega (Standard) / [E]xit: ").strip().lower()

        if mode_input in ["exit", "e"]:
            print("👋 Session ended.\n")
            break
        
        mode = "omega"
        if mode_input in ["a", "alpha"]: mode = "alpha"
        elif mode_input in ["o", "omega"]: mode = "omega"
        else: print("❌ Invalid input. Defaulting to Omega.")

        # 🔍 AUDIT: Verify what parameters are active
        cfg = get_model_config(mode)
        is_reasoning = cfg.model.startswith("o") and not cfg.model.startswith("gpt") or "reasoning" in cfg.model

        print(f"\n✅ Active Profile: {mode.upper()}")
        print(f"   Model: {cfg.model}")
        
        if is_reasoning:
            print(f"   [Reasoning Mode Active]")
            print(f"   - Reasoning Effort: {cfg.reasoning_effort}")
            print(f"   - Temperature:      (IGNORED by Client)")
            print(f"   - Top P:            (IGNORED by Client)")
        else:
            print(f"   [Standard Mode Active]")
            print(f"   - Temperature:      {cfg.temperature}")
            print(f"   - Top P:            {cfg.top_p}")
            print(f"   - Reasoning Effort: (IGNORED by Client)")

        while True:
            user_input = input(f"\n👤 You ({mode.upper()}): ").strip()
            
            if user_input.lower() in ["exit", "e", "back"]: break 
            if not user_input: continue

            user_id, page, name, email = _get_runtime_context()
            history = _build_conversation_history(user_input)
            
            print(f"\n🧠 Thinking with {cfg.model}...")
            start_time = time.time()
            
            try:
                # 🚀 CALL THE CLIENT
                ai_reply, _ = send_message_to_assistant(
                    conversation_input=history,
                    user_id=user_id,
                    page=page,
                    name=name,
                    email=email,
                    mode=mode 
                )
                latency = time.time() - start_time
                
                print(f"\n🤖 Roma AI ({latency:.2f}s):\n{ai_reply}\n")
                
            except Exception as e:
                print(f"\n❌ ERROR ({mode.upper()}): {e}\n")

if __name__ == "__main__":
    main()