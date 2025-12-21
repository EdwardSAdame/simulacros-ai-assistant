# tests/test_structured_quiz.py
import sys
import os
import json
import logging

# --- 1. Setup Path to find 'src' ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.assistant.assistant_client import generate_structured_quiz
from src.config.model_config import get_model_config

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QuizTest")

def test_quiz_generation(mode="omega", topic="Derivadas Implícitas"):
    print(f"\n===============================================")
    print(f"🔹 Testing Structured Quiz Generation")
    print(f"🔹 Mode: {mode.upper()}")
    print(f"🔹 Topic: {topic}")
    print(f"===============================================\n")

    # 1. Verify Config Load
    cfg = get_model_config(mode)
    print(f"✅ Loaded Config for {mode.upper()}:")
    print(f"   - Model: {cfg.model}")
    print(f"   - Temp:  {cfg.temperature}")
    print(f"   - Top_P: {cfg.top_p}")

    # 2. Mock Conversation History
    # This simulates what the ChatService normally builds
    conversation_input = [
        {"role": "user", "content": [{"type": "input_text", "text": f"Generate a quiz about {topic}."}]}
    ]

    # 3. Call the API
    try:
        print("\n⏳ Sending request to OpenAI (Structured Output)...")
        
        # This returns the Pydantic 'QuizResponse' object directly
        quiz_response = generate_structured_quiz(
            conversation_input=conversation_input,
            user_id="test-user",
            page="math-test-page",
            mode=mode
        )

        print("\n🎉 SUCCESS! Received Structured Output:")
        print(f"🗣️  Intro: \"{quiz_response.intro_message}\"")
        print(f"📊 Questions Generated: {len(quiz_response.questions)}")

        # 4. Inspect the First Question to verify Latex/Format
        if quiz_response.questions:
            q1 = quiz_response.questions[0]
            print(f"\n🔎 Inspecting Question 1:")
            print(f"   Title: {q1.question_title}")
            print(f"   Text:  {q1.question_text}")
            print(f"   Correct Index: {q1.correct_option_index}")
            print(f"   Option A: {q1.options[0].text} (Feedback: {q1.options[0].feedback})")
        
        # 5. Verify it dumps to JSON correctly (for frontend)
        json_output = quiz_response.model_dump()
        print(f"\n💾 JSON Dump Test (First 100 chars):")
        print(str(json.dumps(json_output))[:100] + "...")

    except Exception as e:
        print(f"\n❌ FAILED: {e}")

if __name__ == "__main__":
    # You can change this to "alpha" to test your reasoning model
    target_mode = input("Select Mode (alpha/omega): ").strip().lower() or "omega"
    test_quiz_generation(mode=target_mode)