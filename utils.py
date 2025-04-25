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
    Analyzes React code to find used lucide-react icons, checks they aren't
    imported from other sources, and ensures they are correctly imported
    from 'lucide-react'.

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
    component_usage_pattern = re.compile(r"<([A-Z][A-Za-z0-9_]+)(?:\s|/>|>)")
    potential_components_in_jsx = set(component_usage_pattern.findall(code_content))
    print(f"Potential components found in JSX: {potential_components_in_jsx}")

    # 2. Filter potential components to only include actual Lucide icons
    known_icons_set = set(known_lucide_icons)
    used_potential_lucide_icons = {
        comp for comp in potential_components_in_jsx if comp in known_icons_set
    }
    print(
        f"Potential Lucide icons found being used in JSX: {used_potential_lucide_icons}"
    )

    # 3. Find *all* named imports to check for conflicts
    all_imports_pattern = re.compile(
        r'^import\s*\{([^}]*)\}\s*from\s*["\'](.*?)["\'];?', re.MULTILINE
    )
    # Dictionary to store {ComponentName: SourcePath} for non-lucide imports
    other_imports_map: dict[str, str] = {}
    # Set to store components explicitly imported from lucide-react
    current_lucide_imports_set: set[str] = set()
    lucide_import_match = None  # Store the match object for lucide-react import

    for match in all_imports_pattern.finditer(code_content):
        source_path = match.group(2)
        imports_str = match.group(1).strip()
        imports_str_cleaned = re.sub(
            r"//.*?\n|/\*.*?\*/", "", imports_str, flags=re.DOTALL
        )
        imported_items = set(
            i.strip() for i in imports_str_cleaned.split(",") if i.strip()
        )

        if source_path == "lucide-react":
            current_lucide_imports_set = imported_items
            lucide_import_match = match  # Found the specific lucide-react import line
            print(
                f"Icons currently imported from lucide-react: {current_lucide_imports_set}"
            )
        else:
            for item in imported_items:
                if item in other_imports_map:
                    # Handle potential duplicate imports of the same name from different non-lucide sources if necessary
                    print(
                        f"Warning: Component '{item}' imported from multiple non-lucide sources ('{other_imports_map[item]}' and '{source_path}')."
                    )
                other_imports_map[item] = source_path

    print(f"Components imported from other sources: {other_imports_map}")

    # If no lucide-react import line exists, behave as before (or decide to add one)
    if lucide_import_match is None:
        print("Warning: No 'lucide-react' import line found.")
        if used_potential_lucide_icons:
            # Check if any of the used icons conflict with other imports
            conflicts = {
                icon
                for icon in used_potential_lucide_icons
                if icon in other_imports_map
            }
            valid_to_add = used_potential_lucide_icons - conflicts
            if valid_to_add:
                print(
                    f"Found usage of potential Lucide icons not imported elsewhere: {valid_to_add}. Consider adding an import line."
                )
            if conflicts:
                print(
                    f"Found usage of potential Lucide icons that conflict with other imports: {conflicts}"
                )
        return code_content  # Return original code if no lucide import exists

    # 4. Determine the final set of icons that *should* be in the lucide-react import
    #    Start with icons currently imported from lucide-react
    final_lucide_imports_needed = set(current_lucide_imports_set)

    # Add used icons *only if* they are not imported from somewhere else
    for icon in used_potential_lucide_icons:
        if icon not in other_imports_map:
            # If it's used, it's a known Lucide icon, and it's NOT in the other imports,
            # it belongs in the lucide-react import.
            final_lucide_imports_needed.add(icon)
        # else: if icon is in other_imports_map, we intentionally skip adding it here.

    # Remove icons from the final set if they are *no longer used* in JSX
    # (Optional, but good for cleanup):
    # final_lucide_imports_needed = {
    #    icon for icon in final_lucide_imports_needed
    #    if icon in used_potential_lucide_icons or icon in current_lucide_imports_set # Keep if used OR was already there explicitly
    # }
    # --- Simpler approach: Only add based on usage, ignore cleanup for now ---
    # The logic above already achieves: keep current + add used if valid. Let's refine.

    # --- Refined Logic for Step 4 ---
    # The target set is:
    # (Icons currently imported from lucide) UNION (Icons used in JSX AND are known Lucide icons AND NOT imported elsewhere)
    # This ensures we don't remove icons that were manually added but aren't detected in JSX.
    # Let's stick to the requirement: ensure USED icons are correctly imported.

    # Determine REQUIRED icons based *only* on usage analysis, respecting conflicts
    required_lucide_icons_based_on_usage = set()
    conflicting_used_icons = set()
    for icon in used_potential_lucide_icons:
        if icon not in other_imports_map:
            required_lucide_icons_based_on_usage.add(icon)
        else:
            conflicting_used_icons.add(icon)

    if conflicting_used_icons:
        print(
            f"Note: The following components used in JSX are also valid Lucide icons but are imported from other sources: {conflicting_used_icons}. They will NOT be added to 'lucide-react'."
        )

    print(
        f"Required Lucide icons based on usage (excluding conflicts): {required_lucide_icons_based_on_usage}"
    )

    # Sort for consistent comparison and output
    final_import_set_sorted = sorted(list(required_lucide_icons_based_on_usage))
    current_lucide_imports_sorted = sorted(list(current_lucide_imports_set))

    # 5. Check if changes are needed
    if current_lucide_imports_sorted == final_import_set_sorted:
        print(
            "No changes needed for lucide-react imports (already correct and sorted based on usage)."
        )
        return code_content

    # 6. Generate the new import statement
    original_import_statement = lucide_import_match.group(
        0
    )  # The full original line match

    if not final_import_set_sorted:
        new_import_line_content = "{ }"  # Import empty set if no icons needed
    else:
        if len(final_import_set_sorted) > 4:  # Threshold for multiline
            items_str = (
                "\n"
                + ",\n".join([f"  {icon}" for icon in final_import_set_sorted])
                + ",\n"
            )
            new_import_line_content = f"{{{items_str}}}"
        else:
            new_import_list_str = ", ".join(final_import_set_sorted)
            new_import_line_content = f"{{ {new_import_list_str} }}"

    ends_with_semicolon = original_import_statement.rstrip().endswith(";")
    new_import_line = f'import {new_import_line_content} from "lucide-react"'
    if ends_with_semicolon:
        new_import_line += ";"

    # 7. Replace the old import line with the new one
    #    Use re.sub with the original pattern anchored to the start of line
    #    Need to escape the original matched string if using it directly in pattern
    #    Safer: Use the lucide_import_match span to replace, or use the pattern

    # Using the pattern for replacement is generally better
    fixed_code = all_imports_pattern.sub(
        lambda m: new_import_line if m.group(2) == "lucide-react" else m.group(0),
        code_content,
        count=0,  # Replace all occurrences (though should only be one lucide import)
    )
    # Refine replacement: Only replace the *first* match if multiple imports were found (unlikely)
    # Using string replacement based on match span is safer if regex replacement complexifies
    start, end = lucide_import_match.span()
    fixed_code = code_content[:start] + new_import_line + code_content[end:]

    print("Updated lucide-react import line.")
    return fixed_code
