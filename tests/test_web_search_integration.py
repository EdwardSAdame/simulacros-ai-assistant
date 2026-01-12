# tests/test_web_search_integration.py
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to python path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.web_search_config import get_search_filters, ICFES_DOMAINS
from src.assistant.assistant_client import send_message_to_assistant

class TestWebSearchIntegration(unittest.TestCase):

    def test_filter_configuration(self):
        """
        1. Verify that the Context Logic returns the correct domains.
        """
        print("\n🔹 Testing Domain Filters...")
        
        # Case A: ICFES Context
        filters = get_search_filters("ICFES")
        print(f"   [ICFES] Filters: {filters}")
        self.assertIsNotNone(filters)
        # Check if 'icfes.gov.co' is in the allowed list
        # Note: web_search_config logic might add INVICTO_DOMAINS too, so we check inclusion
        allowed = filters["allowed_domains"]
        self.assertTrue(any("icfes.gov.co" in d for d in allowed), "Should include ICFES domain")
        self.assertTrue(any("invicto.com.co" in d for d in allowed), "Should include Invicto domain")

        # Case B: General Context
        filters_general = get_search_filters("GENERAL")
        print(f"   [GENERAL] Filters: {filters_general}")
        self.assertIsNone(filters_general, "General context should return None (Open Web)")

    @patch('src.assistant.assistant_client.get_openai_client')
    @patch('src.assistant.assistant_client.get_model_config')
    def test_web_tool_request_and_citation_parsing(self, mock_get_config, mock_get_client):
        """
        2. Verify that:
           - The 'web_search' tool is sent to OpenAI.
           - The response 'annotations' are correctly converted to Markdown links.
        """
        print("\n🔹 Testing API Request & Citation Parsing...")

        # --- SETUP MOCKS ---
        # Mock Config
        mock_config_instance = MagicMock()
        mock_config_instance.model = "gpt-4o"
        mock_config_instance.temperature = 0.5
        mock_config_instance.top_p = 1.0
        mock_get_config.return_value = mock_config_instance

        # Mock API Response
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = "El examen es en Marzo."
        
        # Simulate the 'output' structure with annotations (The tricky part)
        # Structure: output[0].content[0].annotations[0].url
        mock_annotation = MagicMock()
        mock_annotation.type = "url_citation"
        mock_annotation.url = "https://www.icfes.gov.co/fechas"
        mock_annotation.title = "Calendario 2026"

        mock_content_part = MagicMock()
        mock_content_part.annotations = [mock_annotation]
        
        mock_message_item = MagicMock()
        mock_message_item.type = "message"
        mock_message_item.content = [mock_content_part]

        mock_response.output = [mock_message_item]
        
        # Bind the mock response to the create method
        mock_client_instance.responses.create.return_value = mock_response
        mock_get_client.return_value = mock_client_instance

        # --- EXECUTE ---
        # Simulate a call triggered by the Chat Service with ICFES filters
        fake_filters = {"allowed_domains": ["icfes.gov.co"]}
        
        response_text, assets = send_message_to_assistant(
            conversation_input=[{"role": "user", "content": "When is the exam?"}],
            web_search_config=fake_filters # <--- This is what we are testing
        )

        # --- VERIFY REQUEST (Did we ask for the tool?) ---
        # Get the arguments passed to client.responses.create
        call_args = mock_client_instance.responses.create.call_args[1] # kwargs
        
        self.assertIn("tools", call_args, "Request must contain 'tools'")
        tools_sent = call_args["tools"]
        
        # Find the web_search tool
        web_tool = next((t for t in tools_sent if t["type"] == "web_search"), None)
        self.assertIsNotNone(web_tool, "web_search tool was NOT found in the API request")
        self.assertEqual(web_tool["filters"], fake_filters, "Domain filters were not passed correctly to the API")
        
        print("   ✅ Request correctly included 'web_search' tool with filters.")

        # --- VERIFY RESPONSE (Did we format the link?) ---
        print(f"   [OUTPUT TEXT]: {response_text}")
        
        expected_citation = "- [Calendario 2026](https://www.icfes.gov.co/fechas)"
        self.assertIn("Fuentes Consultadas:", response_text, "Response missing 'Fuentes Consultadas' header")
        self.assertIn(expected_citation, response_text, "Response missing the formatted markdown link")
        
        print("   ✅ Response correctly formatted the citation as a link.")

if __name__ == '__main__':
    unittest.main()