import os
from dotenv import load_dotenv
import openai

# Load .env file
load_dotenv()

# Get credentials
api_key = os.getenv("OPENAI_API_KEY")
assistant_id = os.getenv("OPENAI_ASSISTANT_ID")

assert api_key, "❌ OPENAI_API_KEY not found in .env"
assert assistant_id, "❌ OPENAI_ASSISTANT_ID not found in .env"

client = openai.Client(api_key=api_key)

def test_dynamic_query():
    user_input = input("🧠 Enter your message to Roma: ")

    print("\n🔁 Sending to Assistant...\n")

    # Create new thread
    thread = client.beta.threads.create()

    # Send user message
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input
    )

    # Run Assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    # Wait for completion
    while True:
        status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if status.status in ["completed", "failed", "cancelled"]:
            break

    if status.status != "completed":
        raise Exception(f"❌ Assistant run failed: {status.status}")

    # Retrieve assistant response
    messages = client.beta.threads.messages.list(thread_id=thread.id, order="desc")
    for msg in messages.data:
        if msg.role == "assistant":
            print("✅ Assistant reply:\n")
            print(msg.content[0].text.value)
            return

    print("⚠️ No assistant reply found.")

if __name__ == "__main__":
    test_dynamic_query()
