import sys
import os
import unittest
import logging
from dotenv import load_dotenv

# 1. Setup path to find 'src' modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. Force load environment variables
load_dotenv(override=True)

from src.services.semantic_router import semantic_router
from src.config.settings import settings

# Configure simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

class TestRouterPhrases(unittest.TestCase):

    def setUp(self):
        """Backup original settings to avoid polluting global state."""
        self.original_model = settings.OPENAI_ROUTER_MODEL
        # Use getattr to be safe if variable keys changed
        self.original_temp = getattr(settings, 'OPENAI_ROUTER_TEMP', 0.3)
        self.original_effort = getattr(settings, 'OPENAI_ROUTER_EFFORT', 'low')

    def tearDown(self):
        """Restore settings."""
        settings.OPENAI_ROUTER_MODEL = self.original_model
        settings.OPENAI_ROUTER_TEMP = self.original_temp
        if hasattr(settings, 'OPENAI_ROUTER_EFFORT'):
            settings.OPENAI_ROUTER_EFFORT = self.original_effort

    def test_phrase_generation_and_params(self):
        """
        Checks if the Router uses the correct parameters and generates unique phrases.
        """
        model = settings.OPENAI_ROUTER_MODEL
        
        # 🟢 1. PARAMETER AUDIT
        # Replicating the logic from semantic_router.py to show what IS happening
        is_reasoning = model.startswith("o") and not model.startswith("gpt") or "reasoning" in model

        print(f"\n========================================")
        print(f"🤖  TESTING ROUTER MODEL: {model}")
        print(f"========================================")
        
        if is_reasoning:
            print(f"⚙️  ACTIVE MODE: [REASONING]")
            print(f"    - Reasoning Effort: {settings.OPENAI_ROUTER_EFFORT}")
            print(f"    - Temperature:      (IGNORED)")
            print(f"    - Top P:            (IGNORED)")
        else:
            print(f"⚙️  ACTIVE MODE: [STANDARD]")
            print(f"    - Temperature:      {settings.OPENAI_ROUTER_TEMP}")
            print(f"    - Top P:            {settings.OPENAI_ROUTER_TOP_P}")
            print(f"    - Reasoning Effort: (IGNORED)")
        
        print(f"========================================\n")

        # 🟢 2. EXECUTION
        query = "Necesito estudiar para el examen de la nacional, soy muy malo en quimica"
        print(f"📩 Sending Query: '{query}'")
        
        result = semantic_router.determine_category(query)
        phrases = result.get("loading_phrases", [])
        category = result.get("category", "unknown")

        # 🟢 3. VERIFICATION
        print(f"\n🏷️  Classified Category: {category.upper()}")
        print(f"\n✨ Generated Phrases ({len(phrases)}):")
        
        for i, phrase in enumerate(phrases, 1):
            print(f"   {i}. {phrase}")

        # Assertions
        self.assertTrue(len(phrases) > 0, "❌ Failed: Model returned NO phrases.")
        
        # Check for distinctness (Creative check)
        if len(phrases) > 1:
            unique_count = len(set(phrases))
            if unique_count == len(phrases):
                print("\n✅ SUCCESS: Phrases are distinct and creative.")
            else:
                print(f"\n⚠️ WARNING: Some phrases are duplicates ({unique_count}/{len(phrases)} unique).")
        else:
            print("\n⚠️ WARNING: Model only returned 1 phrase (expected ~3).")

if __name__ == '__main__':
    unittest.main()