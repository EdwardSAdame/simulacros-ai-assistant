import sys
import os
import logging
from dotenv import load_dotenv

# Add the project root to the python path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.assistant.assistant_client import generate_structured_quiz

# Setup logging to see the "Uploaded to S3" messages
logging.basicConfig(level=logging.INFO)

def test_visual_quiz():
    # 1. Load Environment Variables
    load_dotenv()
    
    # 2. Safety Checks
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY is missing in .env")
        return
    
    # Check for AWS Credentials (either in .env or ~/.aws/credentials)
    # We just check if boto3 can find them implicitly, but let's warn if S3 config is missing
    if not os.getenv("S3_BUCKET_NAME"):
        print("⚠️ WARNING: S3_BUCKET_NAME is missing in .env. Uploads might fail.")

    print("\n🚀 STARTING VISUAL QUIZ TEST")
    print("------------------------------------------------")
    print("Subject: Quadratic Functions (Graphing Request)")
    
    # 3. The Prompt (Explicitly asking for a plot)
    conversation = [
        {
            "role": "user", 
            "content": "Generate a short math quiz about parabolas. For the first question, I want you to strictly use the python tool to PLOT the graph of f(x) = x^2 - 4x. The question should ask about the vertex."
        }
    ]

    try:
        # 4. Call the function (Simulating the Lambda Worker)
        quiz_response = generate_structured_quiz(
            conversation_input=conversation,
            user_id="test_local_dev",
            mode="omega" # Ensure you use a smart model (gpt-4o)
        )

        print("\n✅ GENERATION COMPLETE!")
        print(f"Intro: {quiz_response.intro_message}\n")
        
        # 5. Inspect the Questions for URLs
        for i, q in enumerate(quiz_response.questions):
            print(f"[{i+1}] {q.question_title}")
            print(f"    Q: {q.question_text[:50]}...")
            
            # THE MOMENT OF TRUTH
            if q.image_url:
                print(f"    🖼️ IMAGE URL: {q.image_url}")
                if "invicto-quiz-assets" in q.image_url and "https://" in q.image_url:
                     print("    🎉 SUCCESS: Valid S3 URL detected!")
                elif q.image_url == "PENDING_UPLOAD":
                     print("    ⚠️ PENDING: The AI tagged it, but the upload logic didn't replace it.")
            else:
                print("    ⚪ No image for this question.")
            print("-" * 40)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_visual_quiz()