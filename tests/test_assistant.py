# test_assistant.py
from src.config.settings import get_openai_client
from src.config.model_config import get_model_config
from src.config.system_instructions import build_system_instructions
from src.utils.time_utils import get_current_time_info


def main():
    client = get_openai_client()
    cfg = get_model_config()

    # Dummy context
    user_id = "test-user"
    page = "simulacro-unal/ciencias-naturales"
    name = "Test User"
    email = "test@example.com"

    # Build runtime signals
    tinfo = get_current_time_info()
    signals = [
        f"Today is {tinfo['full_human']}.",
        f"The user is on the page: {page}.",
        f"Their user ID is {user_id}.",
        f"Display name: {name}.",
        f"Email: {email}.",
    ]
    system_text = build_system_instructions(extras=signals)

    print("\n🔹 Simple Roma test (type 'exit' to stop)\n")

    while True:
        user_input = input("👤 You: ").strip()
        if user_input.lower() == "exit":
            print("👋 Session ended.\n")
            break
        if not user_input:
            continue

        resp = client.responses.create(
            model=cfg.model,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": system_text}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_input}]},
            ],
        )

        # Extract assistant text
        text = getattr(resp, "output_text", None)
        if not text:
            text = "[No assistant response found]"

        print(f"\n🤖 Roma AI: {text}\n")


if __name__ == "__main__":
    main()
