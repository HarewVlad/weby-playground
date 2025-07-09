import os
import re

script_dir = os.path.dirname(os.path.abspath(__file__))
project_path = os.path.join(script_dir, "website_nextjs/")

os.makedirs(project_path, exist_ok=True)
print(f"[*] Project path set to: {project_path}")


def apply_changes(response_content, base_project_path):
    """
    Parses the response content for <Edit filename="...">...</Edit> blocks,
    handling optional markdown code fences (```) around the content, and
    applies the changes to the specified files within the base_project_path.
    """
    # Updated pattern to specifically handle <Edit> tags
    edit_pattern = re.compile(
        # Match <Edit filename="...">
        r'<Edit\s+filename="([^"]+)"\s*>\s*'
        # Optional ```lang marker and newline
        r"(?:```[a-zA-Z]*\s*\n?)?"
        # Capture the content (non-greedy)
        r"(.*?)"
        # Optional newline and closing ``` marker
        r"(?:\n?\s*```)?"
        # Match the corresponding closing tag </Edit>
        r"\s*</Edit>",
        re.DOTALL | re.IGNORECASE,
    )

    changed = False
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
            print(f"[*] File written to: {abs_target_path}")

            changed = True
        except OSError as e:
            print(f"\n[!] Error writing file '{relative_filename}': {e}")
        except Exception as e:
            print(
                f"\n[!] An unexpected error occurred while processing file '{relative_filename}': {e}"
            )

    return changed
