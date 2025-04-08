import os
import re
from openai import OpenAI
import json
from config import Config
from utils import get_project_structure_detailed

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=Config.OPENROUTER_API_KEY,
)

script_dir = os.path.dirname(os.path.abspath(__file__))
project_path = os.path.join(script_dir, "website")

os.makedirs(project_path, exist_ok=True)
print(f"[*] Project path set to: {project_path}")


def apply_edits(response_content, base_project_path):
    """
    Parses the response content for <edit filename="...">...</edit> blocks,
    handling optional markdown code fences (```) around the content,
    and applies the changes to the specified files within the base_project_path.
    """
    # Regex to find <edit> blocks and capture filename and content
    # It now optionally matches and excludes markdown code fences (```[lang]\n ... \n```)
    # around the core content
    edit_pattern = re.compile(
        r'<edit filename="([^"]+)">\s*'
        r"(?:```[a-zA-Z]*\s*\n?)?"
        r"(.*?)"
        r"(?:\n?\s*```)?"
        r"\s*</edit>",
        re.DOTALL | re.IGNORECASE,
    )
    edits_applied = False
    abs_project_path = os.path.abspath(base_project_path)

    for match in edit_pattern.finditer(response_content):
        relative_filename = match.group(1).strip()
        file_content = match.group(2).strip()

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
            edits_applied = True
        except OSError as e:
            print(f"\n[!] Error writing file '{relative_filename}': {e}")
        except Exception as e:
            print(
                f"\n[!] An unexpected error occurred while processing file '{relative_filename}': {e}"
            )

    return edits_applied


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
            # Prepare context
            try:
                if not os.path.exists(project_path):
                    print(
                        f"\nWarning: Project path '{project_path}' does not exist. Cannot get structure."
                    )
                    project_context = (
                        "Project structure: Not available (directory not found).\n\n"
                    )
                else:
                    project_structure = get_project_structure_detailed(
                        project_path,
                        [
                            "node_modules",
                            ".git",
                            "__pycache__",
                            "dist",
                            "build",
                            "style.css",
                        ],
                    )
                    project_context = f"Current project structure: {json.dumps(project_structure, indent=2)}\n\n"
            except Exception as e:
                print(
                    f"\nWarning: Error getting project structure: {e}. Proceeding without it."
                )
                project_context = f"Project structure: Error retrieving ({e}).\n\n"

            current_user_prompt = project_context + f"User request: {user_input}"

            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": Config.SYSTEM_PROMPT,
                }
            ]

            messages.extend(chat_history[:-1])
            messages.append({"role": "user", "content": current_user_prompt})

            # Call API
            stream = client.chat.completions.create(
                model="google/gemma-3-27b-it",
                messages=messages,
                stream=True,
                # stop=["</edit>"]  # Can help in single file fast editing???
            )

            # Process response
            print("Weby: ", end="", flush=True)
            full_response = ""
            for chunk in stream:
                content_delta = chunk.choices[0].delta.content
                if content_delta is not None:
                    print(content_delta, end="", flush=True)
                    full_response += content_delta
            print()

            # Post-processing
            if full_response:
                apply_edits(full_response, project_path)

                chat_history.append({"role": "assistant", "content": full_response})

            # Limit overall history size
            if len(chat_history) > Config.MAX_CHAT_HISTORY_SIZE:
                chat_history = chat_history[-Config.MAX_CHAT_HISTORY_SIZE :]

        except Exception as e:
            print(f"\n[!] Error processing request: {str(e)}")

        print("-" * 50)


if __name__ == "__main__":
    chat_loop()
