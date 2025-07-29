import os
import time
from openai import OpenAI
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

# ✅ Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def test_assistant():
    """Test OpenAI Assistant with dynamic user input."""
    try:
        thread = client.beta.threads.create()
        print("\n🔹 Test your Assistant (type 'exit' to stop):\n")

        while True:
            user_input = input("👤 You: ").strip()
            if user_input.lower() == "exit":
                print("👋 Session ended.\n")
                break

            # Send user message
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_input
            )

            # Run Assistant (no extra instructions)
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )

            # Wait for completion
            while True:
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id, run_id=run.id
                )
                if run.status in ["completed", "failed"]:
                    break
                time.sleep(0.5)

            # Retrieve response
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            latest_response = messages.data[0].content[0].text.value.strip()

            print(f"🤖 Roma AI: {latest_response}\n")

    except Exception as err:
        print(f"❌ Error during assistant test: {err}")


if __name__ == "__main__":
    test_assistant()
