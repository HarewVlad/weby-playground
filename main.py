import os
from openai import OpenAI
import json
from config import Config
from utils import get_project_structure_detailed

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=Config.OPENROUTER_API_KEY,
)

project_path = os.path.join(os.getcwd(), "website")


def chat_loop():
    print("Welcome to the Weby Chat! Type 'exit' or 'quit' to end the conversation.")
    print("=" * 50)

    chat_history = []

    while True:
        user_input = input("\nYou: ")

        if user_input.lower() in ["exit", "quit"]:
            print("\nExiting chat. Goodbye!")
            break

        chat_history.append({"role": "user", "content": user_input})

        try:
            if len(chat_history) > 1:
                formatted_input = f"User input: {user_input}\n\nChat history:\n"
                max_history = min(16, len(chat_history) - 1)
                for i in range(
                    len(chat_history) - max_history - 1, len(chat_history) - 1
                ):
                    msg = chat_history[i]
                    formatted_input += f"{msg['role'].capitalize()}: {msg['content']}\n"
            else:
                formatted_input = user_input

            project_structure = get_project_structure_detailed(
                project_path, ["node_modules", "style.css"]
            )

            completion = client.chat.completions.create(
                model="google/gemma-3-27b-it",
                messages=[
                    {
                        "role": "system",
                        "content": Config.SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": f"Project structure: {json.dumps(project_structure)}\n\n"
                        + formatted_input,
                    },
                ],
            )

            print("Weby:", completion.choices[0].message.content)

            chat_history.append(
                {"role": "assistant", "content": completion.choices[0].message.content}
            )
        except Exception as e:
            print(f"\nError: {str(e)}")

        print("-" * 50)


if __name__ == "__main__":
    chat_loop()
