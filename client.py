import os
import re
import json
from config import Config
from utils import get_project_structure_detailed
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
project_path = os.path.join(script_dir, "website")

os.makedirs(project_path, exist_ok=True)
print(f"[*] Project path set to: {project_path}")


def apply_changes(response_content, base_project_path):
    """
    Parses the response content for <edit filename="...">...</edit> and
    <create filename="...">...</create> blocks, handling optional markdown
    code fences (```) around the content, and applies the changes to the
    specified files within the base_project_path.
    """
    action_pattern = re.compile(
        # Match <edit filename="..."> or <create filename="...">
        r'<(Edit) filename="([^"]+)">\s*'
        # Optional ```lang marker and newline
        r"(?:```[a-zA-Z]*\s*\n?)?"
        # Capture the content (non-greedy)
        r"(.*?)"
        # Optional newline and closing ``` marker
        r"(?:\n?\s*```)?"
        # Match the corresponding closing tag </Edit>
        r"\s*</\1>",
        re.DOTALL | re.IGNORECASE,
    )
    changes_applied = False
    abs_project_path = os.path.abspath(base_project_path)

    for match in action_pattern.finditer(response_content):
        relative_filename = match.group(2).strip()
        file_content = match.group(3).strip()

        # Prevent path traversal issues
        target_path = os.path.join(abs_project_path, relative_filename)
        abs_target_path = os.path.abspath(target_path)

        # Ensure the target path is within the project directory
        if os.path.commonpath([abs_project_path, abs_target_path]) != abs_project_path:
            print(
                f"\n[!] Security Alert: Attempted file write outside project directory denied: {relative_filename}"
            )
            continue

        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(abs_target_path), exist_ok=True)

            with open(abs_target_path, "w", encoding="utf-8") as f:
                f.write(file_content)

            print(f"\n[*] Applied edit to: {relative_filename}")
            changes_applied = True
        except OSError as e:
            print(f"\n[!] Error writing file '{relative_filename}': {e}")
        except Exception as e:
            print(
                f"\n[!] An unexpected error occurred while processing file '{relative_filename}': {e}"
            )

    return changes_applied


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
            files = get_project_structure_detailed(
                project_path,
                [
                    "node_modules",
                    ".git",
                    "__pycache__",
                    "dist",
                    "build",
                    "style.css",
                    # "package.json",
                    "package-lock.json",
                    ".next",
                    "lib",
                    "public",
                    "tsconfig.json",
                    "next-env.d.ts",
                    "ui",  # shadcn
                ],
            )

            payload = {
                "messages": chat_history,
                "files": files,
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
                            if "error" in chunk:
                                print(f"\n[!] Error from server: {chunk['error']}")
                                break

                            if "choices" in chunk and chunk["choices"]:
                                content_delta = (
                                    chunk["choices"][0]
                                    .get("delta", {})
                                    .get("content", "")
                                )
                                if content_delta:
                                    print(content_delta, end="", flush=True)
                                    full_response += content_delta
                        except json.JSONDecodeError:
                            print(f"\n[!] Error decoding JSON from server: {data}")
                            continue

                print()

            # Post-processing
            if full_response:
                changes_applied = apply_changes(full_response, project_path)
                if changes_applied:
                    print("[*] File changes applied successfully.")

                chat_history.append({"role": "assistant", "content": full_response})

            # Limit overall history size
            if len(chat_history) > Config.MAX_CHAT_HISTORY_SIZE:
                chat_history = chat_history[-Config.MAX_CHAT_HISTORY_SIZE :]

        except requests.exceptions.RequestException as e:
            print(f"\n[!] Error connecting to server: {str(e)}")
        except Exception as e:
            print(f"\n[!] Error processing request: {str(e)}")

        print("-" * 50)


if __name__ == "__main__":
    chat_loop()
