# tests/test_creative_image.py
import os
import base64
import logging

# Set logging to see debug/info messages
logging.basicConfig(level=logging.INFO)

from src.services.creative_image_service import CreativeImageService
from src.config.model_config import get_model_config

class MockStreamManager:
    """
    A mock manager that intercepts WebSocket calls and saves 
    the images locally to verify the streaming logic.
    """
    def send_status(self, message: str, step: str = "processing"):
        print(f"[*] STATUS: {message}")

    def send_partial_image(self, index: int, b64_data: str):
        print(f"[*] STREAM: Received partial image {index}. Saving to disk...")
        try:
            with open(f"local_test_partial_{index}.png", "wb") as f:
                f.write(base64.b64decode(b64_data))
        except Exception as e:
            print(f"[!] Failed to save partial image: {e}")

    def send_final_image(self, b64_data: str, revised_prompt: str = ""):
        print(f"[*] SUCCESS: Final image received.")
        print(f"[*] REVISED PROMPT: {revised_prompt}")
        try:
            with open("local_test_final.png", "wb") as f:
                f.write(base64.b64decode(b64_data))
        except Exception as e:
            print(f"[!] Failed to save final image: {e}")

    def send_error(self, error_message: str):
        print(f"[!] STREAM ERROR: {error_message}")

def run_local_test():
    # 1. Load and print the configuration
    test_mode = "omega"  # You can change this to "alpha" to test the other mode
    cfg = get_model_config(test_mode)
    
    print("\n" + "="*50)
    print(f"--- CONFIGURATION ({test_mode.upper()} MODE) ---")
    print(f"Orchestrator Text Model : {cfg.model}")
    print(f"Image Generation Model  : {cfg.image_model}")
    print(f"Temperature             : {cfg.temperature}")
    print("="*50 + "\n")

    # 2. Setup the mock manager and conversation
    mock_manager = MockStreamManager()
    
    test_conversation = [
        {"role": "user", "content": "Draw me a beautiful lake surrounded by trees at sunset."}
    ]

    print("--- STARTING LOCAL IMAGE GENERATION TEST ---")
    
    # 3. Trigger the service
    final_text, final_images = CreativeImageService.generate_image(
        conversation_input=test_conversation,
        user_id="local_test_user",
        page="/home",
        name="Local Tester",
        email="test@invicto.ai",
        mode=test_mode, 
        stream_manager=mock_manager
    )

    print("\n--- TEST COMPLETED ---")
    print(f"Final Text Response: {final_text}")
    print(f"Total images generated: {len(final_images)}")

if __name__ == "__main__":
    run_local_test()