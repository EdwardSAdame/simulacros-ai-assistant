import sys
import os

# Ensure the root directory is in the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.assistant.assistant_client import stream_chat_response

def test_interactive_function_calling_flow():
    print("=======================================================")
    print(" Testing End-to-End Function Calling (Admissions Data) ")
    print(" Type 'exit' or 'quit' to stop.")
    print("=======================================================\n")
    
    conversation_history = []
    
    while True:
        try:
            # Capture dynamic user input
            user_msg = input("\nYou: ")
            
            if user_msg.lower() in ['exit', 'quit']:
                print("Exiting interactive test...")
                break
                
            if not user_msg.strip():
                continue
                
            # Append user message to history to maintain context
            conversation_history.append({"role": "user", "content": user_msg})
            
            print("AI: ", end="", flush=True)
            
            # Call the streaming client
            stream = stream_chat_response(
                conversation_input=conversation_history,
                user_id="integration_test_user",
                mode="omega", 
                enable_image_generation=False
            )
            
            full_response = ""
            for event in stream:
                # Accumulate and print the text deltas as they stream in
                if getattr(event, "type", "") == "response.output_text.delta":
                    text_chunk = getattr(event, "delta", "")
                    print(text_chunk, end="", flush=True)
                    full_response += text_chunk
                    
            print() # Print a newline when the stream finishes
            
            # Append the AI's final response to the history for follow-up questions
            conversation_history.append({"role": "assistant", "content": full_response})
            
        except KeyboardInterrupt:
            print("\nExiting interactive test...")
            break
        except Exception as e:
            print(f"\n[Error during execution]: {e}")

if __name__ == "__main__":
    test_interactive_function_calling_flow()