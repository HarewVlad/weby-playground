import re
import json
import os


def get_project_structure_detailed(
    project_path, exclude=None, max_file_size=1024 * 1024
):
    """
    Returns the structure of a project as a JSON-serializable list with file contents.

    Args:
        project_path (str): Path to the project directory
        exclude (list, optional): List of folder names to exclude. Defaults to None.
        max_file_size (int, optional): Maximum file size to read in bytes. Defaults to 1MB.

    Returns:
        list: A list of dictionaries with file paths and contents
    """
    if exclude is None:
        exclude = []

    # Check if the path exists
    if not os.path.exists(project_path):
        return [{"error": f"Path {project_path} does not exist"}]

    result = []

    def _traverse(path):
        # Skip if the current directory should be excluded
        if os.path.basename(path) in exclude and path != project_path:
            return

        try:
            # Get items in the directory
            items = sorted(os.listdir(path))
        except (FileNotFoundError, PermissionError):
            # Skip directories we can't access
            return

        for item in items:
            # Get the full path
            item_path = os.path.join(path, item)

            # Skip excluded directories
            if os.path.isdir(item_path) and item in exclude:
                continue

            # Skip excluded files
            if os.path.isfile(item_path) and item in exclude:
                continue

            # Create the properly formatted path starting with "project_path/"
            rel_path = os.path.relpath(item_path, project_path)
            formatted_path = os.path.join(project_path, rel_path)

            if os.path.isfile(item_path):
                try:
                    # Skip files that are too large
                    file_size = os.path.getsize(item_path)
                    if file_size > max_file_size:
                        result.append(
                            {
                                "file_path": formatted_path,
                                "content": f"[File too large: {file_size} bytes]",
                            }
                        )
                        continue

                    # Try to read the file as text
                    with open(item_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Add file information to result
                    result.append({"file_path": formatted_path, "content": content})
                except UnicodeDecodeError:
                    # For binary files, just note that
                    result.append(
                        {"file_path": formatted_path, "content": "[Binary file]"}
                    )
                except (PermissionError, IsADirectoryError) as e:
                    # For files we can't read, just note that
                    result.append(
                        {
                            "file_path": formatted_path,
                            "content": f"[Unable to read content: {str(e)}]",
                        }
                    )
            elif os.path.isdir(item_path):
                # Recurse into subdirectories
                _traverse(item_path)

    # Start traversal from the root
    _traverse(project_path)

    return result


def load_known_icons(file_path: str) -> list[str]:
    """Loads the list of known icon names from a JSON file."""
    try:
        with open(file_path, "r") as f:
            icons = json.load(f)
            if isinstance(icons, list) and all(isinstance(item, str) for item in icons):
                print(f"Successfully loaded {len(icons)} icons from {file_path}")
                return icons
            else:
                print(
                    f"Error: Invalid format in {file_path}. Expected a JSON list of strings."
                )
                return []
    except FileNotFoundError:
        print(f"Error: Icon list file not found at {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while loading icons: {e}")
        return []


def fix_lucide_imports_filtered(
    code_content: str, known_lucide_icons: list[str]
) -> str:
    """
    Analyzes React code content to find used lucide-react icons and ensures
    they are all correctly imported in the 'lucide-react' import statement,
    filtering against a list of known Lucide icons.

    Args:
        code_content: A string containing the React component code.
        known_lucide_icons: A list of strings representing valid Lucide icon names.

    Returns:
        A string with the corrected code, potentially updating the
        'lucide-react' import line. Returns the original code if no
        'lucide-react' import is found or no changes are needed.
    """
    if not known_lucide_icons:
        print(
            "Error: Cannot process imports because the known Lucide icons list is empty or failed to load."
        )
        return code_content

    # 1. Find all potential Component usages (capitalized JSX tags)
    #    Includes self-closing tags <Component /> and opening tags <Component>
    component_usage_pattern = re.compile(r"<([A-Z][A-Za-z0-9_]+)(?:\s|/>|>)")
    potential_components = set(component_usage_pattern.findall(code_content))

    # 2. Filter potential components to only include actual Lucide icons
    known_icons_set = set(known_lucide_icons)
    # --- THIS IS THE SET OF ICONS ACTUALLY USED ---
    used_lucide_icons = {
        comp for comp in potential_components if comp in known_icons_set
    }

    print(f"Potential components found in JSX: {potential_components}")
    print(
        f"Filtered Lucide icons found being used: {used_lucide_icons}"
    )  # This is what should be imported

    # 3. Find the existing lucide-react import statement
    #    Improved regex to handle more whitespace variations and potential comments (basic)
    import_pattern = re.compile(
        r'^(import\s*\{([^}]*)\}\s*from\s*["\']lucide-react["\'];?)', re.MULTILINE
    )
    match = import_pattern.search(code_content)

    if not match:
        print("Warning: No 'lucide-react' import line found.")
        # If Lucide icons were detected but no import line exists, we could add one.
        # For now, modifying existing imports only.
        if used_lucide_icons:
            print(
                f"Found usage of Lucide icons but no import line: {used_lucide_icons}"
            )
        return code_content

    original_import_statement = match.group(0)  # Capture the whole matched line
    imports_str = match.group(2).strip() if match.group(2) else ""
    # Trailing chars like semicolon are now part of group(0)

    # 4. Parse the currently imported icons from the matched string
    #    Handle potential trailing commas and comments (basic removal)
    imports_str_cleaned = re.sub(
        r"//.*?\n|/\*.*?\*/", "", imports_str, flags=re.DOTALL
    )  # Remove comments
    current_imports = set(
        i.strip()
        for i in imports_str_cleaned.split(",")
        if i.strip()  # Ensure non-empty strings after stripping
    )

    print(f"Icons currently imported: {current_imports}")

    # 5. Determine the final set of icons to import
    #    *** Correction: The final set IS the set of used icons ***
    #    Sort them alphabetically for consistency.
    final_import_set_sorted = sorted(list(used_lucide_icons))

    print(
        f"Final set of icons to import (based on usage): {set(final_import_set_sorted)}"
    )  # Print as set for clarity

    # 6. Check if changes are needed
    #    Compare the content (as sets) of current imports vs required imports.
    #    Also regenerate if the sorting changes, even if content is the same.
    current_imports_sorted = sorted(list(current_imports))

    if current_imports_sorted == final_import_set_sorted:
        print(
            "No changes needed for lucide-react imports (already correct and sorted)."
        )
        return code_content
    # Handle case where no icons are used, should result in empty import {}
    # This case is covered by the generation logic below if final_import_set_sorted is empty

    # 7. Generate the new import statement
    if not final_import_set_sorted:
        # If no known Lucide icons are used, import nothing.
        new_import_line_content = "{ }"
    else:
        # Format with spaces and trailing comma for better linting/formatting compatibility
        # Adjust formatting as preferred (e.g., multiline for many imports)
        if len(final_import_set_sorted) > 4:  # Example threshold for multiline
            items_str = (
                "\n"
                + ",\n".join([f"  {icon}" for icon in final_import_set_sorted])
                + ",\n"
            )
            new_import_line_content = f"{{{items_str}}}"
        else:
            new_import_list_str = ", ".join(final_import_set_sorted)
            new_import_line_content = f"{{ {new_import_list_str} }}"

    # Check if original import line ended with a semicolon
    ends_with_semicolon = original_import_statement.rstrip().endswith(";")
    new_import_line = f'import {new_import_line_content} from "lucide-react"'
    if ends_with_semicolon:
        new_import_line += ";"

    # Ensure we add a newline if the original line likely had one (simple check)
    # This replacement might be slightly off if the original had complex whitespace,
    # but usually replacing the whole line found by the MULTILINE regex is correct.
    if "\n" in original_import_statement:
        # Add newline if original likely had one, unless it's the last line
        pass  # The replacement below handles the line break implicitly

    # 8. Replace the old import line with the new one
    #    Use re.sub for safer replacement based on the pattern match
    fixed_code = import_pattern.sub(new_import_line, code_content, count=1)

    print("Updated lucide-react import line.")
    return fixed_code
