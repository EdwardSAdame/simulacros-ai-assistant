# tests/test_creative_image.py
import os
import sys
import base64
import logging
import urllib.request

# Add the project root to the path so absolute imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set logging to see debug/info messages
logging.basicConfig(level=logging.INFO)

from src.services.creative_image_service import CreativeImageService
from src.config.model_config import get_model_config
from src.config.settings import get_image_generation_size, get_image_generation_partials

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
            if b64_data.startswith("http"):
                urllib.request.urlretrieve(b64_data, f"local_test_partial_{index}.png")
            else:
                with open(f"local_test_partial_{index}.png", "wb") as f:
                    f.write(base64.b64decode(b64_data))
        except Exception as e:
            print(f"[!] Failed to save partial image: {e}")

    def send_final_image(self, b64_data: str, revised_prompt: str = ""):
        print(f"[*] SUCCESS: Final image received.")
        print(f"[*] REVISED PROMPT: {revised_prompt}")
        try:
            if b64_data.startswith("http"):
                urllib.request.urlretrieve(b64_data, "local_test_final.png")
            else:
                with open("local_test_final.png", "wb") as f:
                    f.write(base64.b64decode(b64_data))
        except Exception as e:
            print(f"[!] Failed to save final image: {e}")

    def send_usage_metrics(self, data: dict):
        print(f"[*] USAGE METRICS TRACKED: {data}")

    def send_error(self, error_message: str):
        print(f"[!] STREAM ERROR: {error_message}")

def main():
    print("==================================================")
    print("INVICTO AI - DYNAMIC IMAGE GENERATION TESTER")
    print("==================================================")
    
    # 1. Choose the Mode Interactively
    mode_input = input("Select Mode (omega/alpha) [default: omega]: ").strip().lower()
    mode = mode_input if mode_input in ["alpha", "omega"] else "omega"
    
    # 2. Load the Configuration securely from .env logic
    cfg = get_model_config(mode)
    size = get_image_generation_size()
    partials = get_image_generation_partials()
    
    print("\nConfiguration Loaded Successfully:")
    print(f"  - Mode:     {mode.upper()}")
    print(f"  - Engine:   {cfg.image_model}")
    print(f"  - Quality:  {cfg.image_quality}")
    print(f"  - Size:     {size}")
    print(f"  - Partials: {partials}")
    print("==================================================\n")

    mock_manager = MockStreamManager()

    # 3. Interactive Infinite Loop
    while True:
        try:
            user_prompt = input("\nEnter your image prompt (or type 'exit' to quit):\n> ")
            if user_prompt.strip().lower() in ['exit', 'quit', 'q']:
                print("Exiting tester. Goodbye!")
                break
                
            if not user_prompt.strip():
                continue

            test_conversation = [
                {"role": "user", "content": user_prompt}
            ]

            print("\nSending request to CreativeImageService...")
            
            # Trigger the actual service used in production
            service_result = CreativeImageService.generate_image(
                conversation_input=test_conversation,
                user_id="local_test_user",
                page="/home",
                name="Local Tester",
                email="test@invicto.ai",
                mode=mode, 
                stream_manager=mock_manager
            )

            # Safely unpack the tuple regardless of length
            final_text = service_result[0] if len(service_result) > 0 else ""
            final_images = service_result[1] if len(service_result) > 1 else []

            print("\n--- GENERATION COMPLETED ---")
            print(f"Final Text Response: {final_text}")
            print(f"Total images generated: {len(final_images) if final_images else 0}")
            print("-" * 50)

        except KeyboardInterrupt:
            print("\nExiting tester. Goodbye!")
            break
        except Exception as e:
            print(f"\nError during generation: {e}")
            print("-" * 50)

if __name__ == "__main__":
    main()