import sys
import os
import json
import logging

# Ensure we can find the src module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.assistant.assistant_client import generate_structured_quiz
from src.config.model_config import get_model_config
from src.services.quiz_service import QuizService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QuizTest")

def test_quiz_generation(mode="omega", topic="Derivadas Implícitas"):
    print(f"\n===============================================")
    print(f"🔹 Testing Structured Quiz Generation (Strict 3 Questions)")
    print(f"🔹 Mode: {mode.upper()}")
    print(f"🔹 Topic: {topic}")
    print(f"===============================================\n")

    # 1. Build Conversation Input (Exactly like ChatService)
    # We explicitly ask for 3 questions here to verify the prompt works
    system_instruction = QuizService.get_system_instruction(topic=topic, num_questions=3)
    
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
        
        # 3. DUMP FULL RESPONSE OBJECT ATTRIBUTES
        print(f"\n📋 Checking Raw Response Attributes:")
        print(f"   [attr] .title:         {getattr(quiz_response, 'title', 'MISSING')}")
        print(f"   [attr] .intro_message: {getattr(quiz_response, 'intro_message', 'MISSING')}")
        print(f"   [attr] .questions:     {len(quiz_response.questions)} items")

        # 4. SIMULATE METADATA CONSTRUCTION (Exact logic from chat_service.py)
        # This determines what actually gets saved to DynamoDB
        
        ai_generated_title = getattr(quiz_response, "title", "Simulacro Personalizado")
        
        metadata_payload = {
            "quiz_mode": "batch",
            "topic": ai_generated_title, # <--- THIS IS THE KEY FIELD
            "questions": [q.dict() for q in quiz_response.questions]
        }

        print(f"\n💾 SIMULATED METADATA PAYLOAD (To be saved in DynamoDB):")
        print(json.dumps(metadata_payload, indent=2, ensure_ascii=False))
        
        # Validation
        if "topic" in metadata_payload:
            print(f"\n✅ PASS: 'topic' field is present: '{metadata_payload['topic']}'")
        else:
            print(f"\n❌ FAIL: 'topic' field is MISSING in the payload.")

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_quiz_generation()