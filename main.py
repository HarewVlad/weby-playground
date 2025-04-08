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
if not os.path.exists(project_path):
    print(f"Warning: Project path '{project_path}' does not exist.")


def chat_loop():
    print("Welcome to the Weby Chat! Type 'exit' or 'quit' to end the conversation.")
    print("=" * 50)

    chat_history = []

    while True:
        try:
            user_input = input("\nYou: ")
        except EOFError:
            print("\nExiting chat. Goodbye!")
            break

        if user_input.lower() in ["exit", "quit"]:
            print("\nExiting chat. Goodbye!")
            break

        chat_history.append({"role": "user", "content": user_input})

        try:
            formatted_input = f"User input: {user_input}\n"
            if len(chat_history) > 1:
                formatted_input += "\nChat history:\n"
                # Limit history length to avoid overly large prompts
                max_history = min(16, len(chat_history) - 1)
                history_start_index = len(chat_history) - 1 - max_history
                for i in range(history_start_index, len(chat_history) - 1):
                    msg = chat_history[i]
                    formatted_input += f"{msg['role'].capitalize()}: {msg['content']}\n"

            try:
                project_structure = get_project_structure_detailed(
                    project_path, ["node_modules", ".git", "__pycache__", "style.css"]
                )
                project_context = (
                    f"Project structure: {json.dumps(project_structure, indent=2)}\n\n"
                )
            except FileNotFoundError:
                print(
                    f"\nWarning: Could not find project path '{project_path}'. Proceeding without project structure."
                )
                project_context = "Project structure: Not available.\n\n"
            except Exception as e:
                print(
                    f"\nWarning: Error getting project structure: {e}. Proceeding without it."
                )
                project_context = "Project structure: Error retrieving.\n\n"

            messages = [
                {
                    "role": "system",
                    "content": Config.SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": project_context + formatted_input,
                },
            ]

            stream = client.chat.completions.create(
                model="google/gemma-3-27b-it",
                messages=messages,
                stream=True,
            )

            print("Weby: ", end="", flush=True)
            full_response = ""
            for chunk in stream:
                content_delta = chunk.choices[0].delta.content
                if content_delta is not None:
                    print(content_delta, end="", flush=True)
                    full_response += content_delta

            print()

            if full_response:  # Only add if we received something
                chat_history.append({"role": "assistant", "content": full_response})
            # Limit overall history size to prevent excessive memory usage/prompt length
            # Keep system prompt + last N user/assistant pairs
            max_total_history_messages = 30  # Keep roughly 15 turns + system prompt
            if len(chat_history) > max_total_history_messages:
                # Keep the first (system) and the last N messages
                chat_history = (
                    chat_history[:1] + chat_history[-(max_total_history_messages - 1) :]
                )

        except Exception as e:
            print(f"\nError processing request: {str(e)}")
            # Optionally remove the last user message if the API call failed
            if chat_history and chat_history[-1]["role"] == "user":
                chat_history.pop()

        print("-" * 50)


if __name__ == "__main__":
    chat_loop()
