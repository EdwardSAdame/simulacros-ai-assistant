# tests/test_structured_quiz.py
import sys
import os
import json
import logging

# Ensure we can find the src module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.assistant.assistant_client import generate_structured_quiz
from src.services.quiz_service import QuizService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QuizTest")

def test_quiz_generation(mode="omega", topic="Derivadas Implícitas"):
    print(f"\n===============================================")
    print(f"🔹 Testing Structured Quiz (Distractor Protocol Verification)")
    print(f"🔹 Mode: {mode.upper()}")
    print(f"🔹 Topic: {topic}")
    print(f"===============================================\n")

    # 1. Build Conversation Input
    # We ask for 1 question to keep the output readable and focus on the logic quality
    system_instruction = QuizService.get_system_instruction(topic=topic, num_questions=1)
    
    conversation_input = [
        system_instruction, 
        {"role": "user", "content": [{"type": "input_text", "text": f"Genera el simulacro sobre {topic}."}]}
    ]

    # 2. Call the API
    try:
        print("\n⏳ Sending request to OpenAI (Structured Output)...")
        
        quiz_response = generate_structured_quiz(
            conversation_input=conversation_input,
            user_id="test-user-dev",
            page="test-page",
            mode=mode
        )

        print("\n🎉 SUCCESS! Received Response Object.")
        
        # 3. VERIFY DISTRACTOR LOGIC (The new feature)
        if quiz_response.questions:
            q = quiz_response.questions[0]
            print(f"\n❓ QUESTION: {q.question_text}")
            print(f"✅ CORRECT ANSWER INDEX: {q.correct_option_index}")
            
            print(f"\n🧠 AI REASONING (Verification of Failure Paths):")
            print("=" * 60)
            # This is where we check if it generated the 'Success Path' and 'Failure Paths'
            print(q.explanation) 
            print("=" * 60)
            
            print(f"\n👇 OPTIONS GENERATED (Check if Distractors match Failure Paths):")
            for i, opt in enumerate(q.options):
                status = "✅ CORRECT" if i == q.correct_option_index else "❌ DISTRACTOR"
                print(f"   [{i}] {opt.text} ({status})")
                print(f"       Feedback: {opt.feedback}")
        
        # 4. METADATA VALIDATION (Standard check)
        ai_generated_title = getattr(quiz_response, "title", "Simulacro Personalizado")
        metadata_payload = {
            "quiz_mode": "batch",
            "topic": ai_generated_title,
            "questions": [q.dict() for q in quiz_response.questions]
        }

        print(f"\n💾 METADATA PAYLOAD CHECK:")
        if "topic" in metadata_payload:
            print(f"   ✅ PASS: 'topic' field is present: '{metadata_payload['topic']}'")
        else:
            print(f"   ❌ FAIL: 'topic' field is MISSING.")

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_quiz_generation()