# tests/test_semantic_router.py
import sys
import os
import unittest
from unittest.mock import MagicMock

# 1. Setup Dummy Environment BEFORE importing the service
# This prevents the Settings class from complaining about missing keys
os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
os.environ["OPENAI_ROUTER_MODEL"] = "gpt-4o-mini"

# 2. Add the project root to the system path so imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 3. Import the router
from src.services.semantic_router import semantic_router

class TestSemanticRouter(unittest.TestCase):
    
    def setUp(self):
        """
        Before each test, we disable the actual OpenAI call.
        We want to test strictly the REGEX logic here.
        """
        # If the code falls back to the AI, return a special flag string
        semantic_router._classify_with_llm = MagicMock(return_value="[FALLBACK_TO_AI]")

    def test_biology_regex(self):
        """Test that biology keywords trigger the correct status instantly."""
        inputs = [
            "Tell me about the mitochondria",
            "What is a cell?",
            "Explain DNA structure",
            "Como funciona el sistema nervioso?",
            "virus and bacteria differences"
        ]
        expected = "Consultando base de datos biológica..."
        
        for text in inputs:
            result = semantic_router.determine_status(text)
            self.assertEqual(result, expected, f"Failed on input: {text}")

    def test_math_regex(self):
        """Test that math keywords trigger the correct status instantly."""
        inputs = [
            "Calculate the integral of x",
            "Solve this equation",
            "física y vectores",
            "cual es la velocidad de la luz?",
            "suma de angulos"
        ]
        expected = "Analizando lógica matemática..."
        
        for text in inputs:
            result = semantic_router.determine_status(text)
            self.assertEqual(result, expected, f"Failed on input: {text}")

    def test_history_regex(self):
        """Test that history keywords trigger the correct status instantly."""
        inputs = [
            "Who was the first president?",
            "La revolución francesa",
            "Historia de Colombia",
            "derechos del ciudadano"
        ]
        expected = "Consultando archivos históricos..."
        
        for text in inputs:
            result = semantic_router.determine_status(text)
            self.assertEqual(result, expected, f"Failed on input: {text}")

    def test_fallback_trigger(self):
        """
        Test that ambiguous words correctly bypass the Regex and hit the AI.
        We expect our Mock return value here.
        """
        inputs = [
            "Tell me about dolphins", # 'dolphins' is not in our keyword list
            "Why is the sky blue?",
            "Hello world"
        ]
        expected = "[FALLBACK_TO_AI]"
        
        for text in inputs:
            result = semantic_router.determine_status(text)
            self.assertEqual(result, expected, f"Regex should have failed for: {text}")

if __name__ == '__main__':
    print("\n🧪 Running Semantic Router Regex Tests...\n")
    unittest.main(verbosity=2)