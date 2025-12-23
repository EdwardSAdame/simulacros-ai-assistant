import sys
import os
import logging
from dotenv import load_dotenv

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.chat_service import get_ai_response

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_rich_chat_generation():
    # 1. Load Environment Variables
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY is missing.")
        return
    if not os.getenv("S3_BUCKET_NAME"):
        print("⚠️ WARNING: S3_BUCKET_NAME is missing. Image upload might fail.")

    print("\n🚀 STARTING RICH CHAT TEST (Standard Chat + Images)")
    print("------------------------------------------------")
    
    # 2. The Prompt (Explicitly asking for a plot in CHAT mode)
    user_message = "Plot the function f(x) = sin(x) * x over the range -10 to 10."
    print(f"User Message: {user_message}")

    try:
        # 3. Call the Service (Simulating the Lambda Worker)
        # We pass intent="chat" to trigger the new logic branch
        text_reply, conv_id, timestamp, meta_payload = get_ai_response(
            message=user_message,
            user_id="test_rich_chat_user",
            name="Tester",
            email="test@example.com",
            page="/math-test",
            mode="omega", # Use GPT-4o for best code generation
            intent="chat"
        )

        print("\n✅ GENERATION COMPLETE!")
        print("------------------------------------------------")
        print(f"🤖 Text Reply:\n{text_reply[:100]}... [truncated]")
        print("------------------------------------------------")

        # 4. Verify Metadata (The Moment of Truth)
        if meta_payload:
            print(f"📦 Metadata Type: {meta_payload.get('type')}")
            
            if meta_payload.get("type") == "rich_chat":
                assets = meta_payload.get("assets", [])
                print(f"🖼️  Assets Found: {len(assets)}")
                
                for i, asset in enumerate(assets):
                    url = asset.get("url")
                    print(f"   [{i+1}] URL: {url}")
                    
                    if "https://" in url and ("s3" in url or "amazonaws" in url or "invicto" in url):
                        print("   🎉 SUCCESS: Valid S3 URL detected!")
                    else:
                        print("   ⚠️  WARNING: URL looks suspicious or empty.")
            else:
                 print(f"⚠️ Unexpected metadata type: {meta_payload}")
        else:
            print("❌ FAILURE: No metadata returned. The image was not captured.")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rich_chat_generation()