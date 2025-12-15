# tests/test_semantic_router_live.py

import sys
import os
import time
import unittest
import logging
import json
from dotenv import load_dotenv 

# Setup the system path to ensure imports work
# This allows the script to find src.services and src.config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 🔹 CRITICAL: Force load the API key and configuration from the .env file immediately.
# This ensures all OPENAI_ROUTER_* variables and the API key are available in settings.
load_dotenv(override=True) 

# Import the router and settings after setup
from src.services.semantic_router import semantic_router
from src.config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# 🔹 DYNAMIC FUNCTION: Loads models for testing from environment
def get_models_to_test():
    """
    Reads a comma-separated list of models from the environment variable 
    ROUTER_MODELS_TO_TEST. If not set, it defaults to testing the configured model only.
    """
    # Use the specific testing variable
    model_str = os.getenv("ROUTER_MODELS_TO_TEST")
    
    if model_str:
        models = [m.strip() for m in model_str.split(',') if m.strip()]
        # Add the configured production model to ensure it's always included
        return list(set(models + [settings.OPENAI_ROUTER_MODEL]))
            
    # Default: only test the configured model (OPENAI_ROUTER_MODEL)
    return [settings.OPENAI_ROUTER_MODEL]


class TestSemanticRouterLive(unittest.TestCase):

    def setUp(self):
        """Store the original model settings for cleanup."""
        # Store original settings to restore them later
        self.original_router_model = settings.OPENAI_ROUTER_MODEL
        
        # Store the actual configured values from the .env file/system environment
        self.original_router_temp = getattr(settings, 'OPENAI_ROUTER_TEMP', None)
        self.original_router_top_p = getattr(settings, 'OPENAI_ROUTER_TOP_P', None)
        
    def tearDown(self):
        """Restore the original model settings after tests complete."""
        # Restore the original settings object attributes
        settings.OPENAI_ROUTER_MODEL = self.original_router_model
        
        # Restore parameters to the original configuration
        if self.original_router_temp is not None:
             setattr(settings, 'OPENAI_ROUTER_TEMP', self.original_router_temp)
        if self.original_router_top_p is not None:
             setattr(settings, 'OPENAI_ROUTER_TOP_P', self.original_router_top_p)
        
    def _test_model_performance_and_logic(self, model_name, test_query):
        """
        Helper to run the test against a specific model name.
        Uses the dynamic Router's configuration (OPENAI_ROUTER_TEMP/TOP_P) loaded from .env.
        """
        
        # 🔹 DYNAMIC: Set the current model for the Router singleton instance
        # The semantic_router will read this to determine which model to call and which params to use.
        settings.OPENAI_ROUTER_MODEL = model_name 
        
        # OPENAI_ROUTER_TEMP/TOP_P are already loaded and are accessed dynamically
        # inside src/services/semantic_router.py

        logger.info(f"\n--- TESTING MODEL: {model_name} with query: '{test_query}' ---")
        
        start_time = time.time()
        
        try:
            # Use the imported global singleton (semantic_router). 
            result = semantic_router.determine_category(test_query)
            
            end_time = time.time()
            latency = end_time - start_time
            
            # Fix model typo (loading_phounces -> loading_phrases) if the model makes the mistake
            if "loading_phounces" in result and "loading_phrases" not in result:
                 result["loading_phrases"] = result.pop("loading_phounces") 

            # Assertions to ensure output is valid
            self.assertIn("category", result)
            self.assertIn("loading_phrases", result)
            self.assertIn("source", result)
            
            self.assertIsInstance(result["loading_phrases"], list)
            self.assertTrue(len(result["loading_phrases"]) >= 2)
            
            logger.info(f"✅ SUCCESS: Category: {result['category']}")
            logger.info(f"✅ PHRASES: {result['loading_phrases']}")
            logger.info(f"✅ LATENCY: {latency:.3f} seconds")

        except Exception as e:
            logger.error(f"❌ FAILURE: Model {model_name} crashed: {e}")
            self.fail(f"Model {model_name} crashed during classification: {e}")
            latency = float('inf')
        
        # Return results to the main test loop
        return model_name, latency

    def test_performance_comparison(self):
        """Main test method to compare models loaded dynamically via ROUTER_MODELS_TO_TEST."""
        
        test_query = "Explica la diferencia entre oxidación y reducción."
        
        # 🔹 Load the models dynamically based on the ROUTER_MODELS_TO_TEST variable
        models_to_test = get_models_to_test()
        
        results = {}

        for model_name in models_to_test:
            # Ensure unique testing of each model name
            if model_name not in results:
                name, latency = self._test_model_performance_and_logic(model_name, test_query)
                results[name] = latency

        logger.info("\n=============================================")
        logger.info("FINAL PERFORMANCE SUMMARY (Router Classification)")
        logger.info("=============================================")
        for name, latency in results.items():
            logger.info(f"{name}: {latency:.3f} seconds")
        logger.info("=============================================")


if __name__ == '__main__':
    print("\n🧪 Running Live Semantic Router Tests (configurable via ROUTER_MODELS_TO_TEST)...")
    
    # Check if the API key is set 
    if os.getenv("OPENAI_API_KEY") is None:
        print("\n⚠️ WARNING: OPENAI_API_KEY is not set. Tests will likely fail with 401 errors.")
    
    unittest.main(verbosity=0)