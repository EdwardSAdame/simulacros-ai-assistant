import sys
import os
import time
import logging
import unittest
from dotenv import load_dotenv

# --- 1. Setup Path to find 'src' ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 2. Force Load Environment Variables ---
load_dotenv(override=True)

from src.assistant.assistant_client import send_message_to_assistant
from src.config.model_config import get_model_config
from src.config.web_search_config import get_search_filters

# Configure simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

class TestLiveWebSearch(unittest.TestCase):

    def test_live_deep_research(self):
        """
        Performs a REAL Web Search using the parameters defined in your .env file.
        """
        # 🟢 1. LOAD CONFIGURATION
        # We load 'omega' just to get access to the global search params inside the object
        cfg = get_model_config("omega") 
        search_model = cfg.search_model
        
        print(f"\n========================================")
        print(f"🌍  LIVE WEB SEARCH TEST (Deep Research)")
        print(f"========================================")
        print(f"⚙️  Active Search Model: {search_model}")
        
        # Audit Parameters
        is_reasoning = search_model.startswith("o") and not search_model.startswith("gpt") or "reasoning" in search_model
        if is_reasoning:
            print(f"    - Mode: [REASONING]")
            print(f"    - Effort: {cfg.search_reasoning_effort}")
            print(f"    - Temp/TopP: (IGNORED)")
        else:
            print(f"    - Mode: [STANDARD]")
            print(f"    - Temp: {cfg.search_temperature}")
            print(f"    - Top P: {cfg.search_top_p}")
            
        print(f"========================================\n")

        # 🟢 2. DEFINE REAL QUERY & CONTEXT
        # A query that requires up-to-date info (2025/2026)
        query = "Cuales son las fechas del examen ICFES Saber 11 para el segundo semestre del 2025?"
        context_key = "ICFES"
        
        print(f"📩 Query: '{query}'")
        
        # Get Real Filters
        filters = get_search_filters(context_key)
        print(f"🔍 Domain Filters: {filters['allowed_domains'] if filters else 'OPEN WEB'}")

        # 🟢 3. EXECUTE REAL API CALL
        print(f"\n🧠  Thinking... (This may take 10-30s for reasoning models)...")
        start_time = time.time()
        
        try:
            conversation_input = [{"role": "user", "content": [{"type": "input_text", "text": query}]}]
            
            response_text, assets = send_message_to_assistant(
                conversation_input=conversation_input,
                user_id="test-user-live",
                page="simulacro-icfes-test",
                web_search_config=filters,
                model_override=search_model # <--- Triggers the Search Config switch
            )
            
            latency = time.time() - start_time
            
            # 🟢 4. RESULTS
            print(f"\n🤖  Response ({latency:.2f}s):\n")
            print(response_text)
            print(f"\n========================================\n")

            # 🟢 5. VERIFICATION
            self.assertTrue(len(response_text) > 50, "❌ Response is suspiciously short.")
            
            if "Fuentes Consultadas" in response_text:
                print("✅  SUCCESS: Citations found and formatted.")
            else:
                print("⚠️  WARNING: Response generated but NO citations were found.")
                
        except Exception as e:
            print(f"\n❌  CRITICAL FAILURE: {e}")
            self.fail(f"API Call Failed: {e}")

if __name__ == '__main__':
    # Verify API Key exists before running
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY not found in .env")
    else:
        unittest.main()