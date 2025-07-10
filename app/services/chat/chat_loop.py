import json
import os

import requests

from app.components.config import Config
from app.utils.chat.apply_changes import apply_changes
from app.utils.chat.edit_tags import check_for_complete_edit_tags
from app.utils.files.project_structure import get_project_structure_detailed

script_dir = os.path.dirname(os.path.abspath(__file__))
project_path = os.path.join(script_dir, "website_nextjs/")

os.makedirs(project_path, exist_ok=True)
print(f"[*] Project path set to: {project_path}")


def chat_loop():
    print("Welcome to the Weby Chat! Type 'exit' or 'quit' to end the conversation.")
    print("=" * 50)

    chat_history = []

    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit"]:
                print("\nExiting chat. Goodbye!")
                break
        except EOFError:
            print("\nExiting chat. Goodbye!")
            break

        chat_history.append({"role": "user", "content": user_input})

        try:
            files = get_project_structure_detailed(
                project_path=project_path,
                exclude=[
                    "favicon.ico",
                    "globals.css",
                    "layout.tsx",
                ],
            )

            payload = {
                "messages": chat_history,
                # "files": files,  # Uncomment if you want to send files
                "temperature": 0.6,
                # "framework": "HTML",
            }

            with requests.post(
                    Config.WEBY_API + "/v1/weby", json=payload, stream=True
            ) as response:
                response.raise_for_status()

                print("Weby: ", end="", flush=True)
                full_response = ""

                for line in response.iter_lines():
                    if line:
                        # Strip the "data: " prefix from SSE format
                        line_text = line.decode("utf-8")
                        if not line_text.startswith("data: "):
                            continue

                        data = line_text[6:]  # Skip "data: "

                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)

                            # Check for error first
                            if "error" in chunk and chunk["error"]:
                                print(
                                    f"\n[!] Error from server: {chunk['error'].get('details', chunk['error'])}"
                                )
                                break

                            # The server wraps the ChatCompletionChunk in a ChatCompletionResponseChunk
                            # which has a structure like: {"data": {...}, "error": None}
                            if (
                                    "data" in chunk
                                    and chunk["data"]
                                    and "choices" in chunk["data"]
                            ):
                                choice = chunk["data"]["choices"][0]
                                content_delta = choice.get("delta", {}).get(
                                    "content", ""
                                )

                                if content_delta:
                                    print(content_delta, end="", flush=True)
                                    full_response += content_delta

                        except json.JSONDecodeError:
                            print(f"\n[!] Error decoding JSON from server: {data}")
                            continue

                print()

            # Post-processing: Apply file changes after streaming is complete
            if full_response:
                print("\n[*] Processing response for file changes...")

                # Check if there are any Edit tags to process
                if check_for_complete_edit_tags(full_response):
                    print("[*] Found Edit tags, applying changes...")
                    changed = apply_changes(full_response, project_path)
                    if changed:
                        print("[*] File changes applied successfully.")
                    else:
                        print("[*] No valid file changes found.")
                else:
                    print("[*] No Edit tags found in response.")

                chat_history.append({"role": "assistant", "content": full_response})

            # Limit overall history size
            if len(chat_history) > Config.MAX_CHAT_HISTORY_SIZE:
                chat_history = chat_history[-Config.MAX_CHAT_HISTORY_SIZE:]

        except requests.exceptions.RequestException as e:
            print(f"\n[!] Error connecting to server: {str(e)}")
        except Exception as e:
            print(f"\n[!] Error processing request: {str(e)}")

        print("-" * 50)


if __name__ == "__main__":
    chat_loop()
