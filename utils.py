import os


def get_project_structure(project_path, exclude=None):
    """
    Returns the structure of a project as a string.

    Args:
        project_path (str): Path to the project directory
        exclude (list, optional): List of folder names to exclude. Defaults to None.

    Returns:
        str: A string representation of the project structure
    """
    if exclude is None:
        exclude = []

    # Check if the path exists
    if not os.path.exists(project_path):
        return f"Path {project_path} does not exist"

    # Check if the path is a file
    if os.path.isfile(project_path):
        return f"{os.path.basename(project_path)} (file)"

    result = []

    def _traverse(path, prefix=""):
        # Get items in the directory
        try:
            items = sorted(os.listdir(path))
        except (FileNotFoundError, PermissionError):
            return

        # Filter out excluded items
        items = [item for item in items if item not in exclude]

        # Process each item
        for i, item in enumerate(items):
            # Get the full path
            item_path = os.path.join(path, item)

            # Check if this is the last item
            is_last = i == len(items) - 1

            # Add the item to the result
            if is_last:
                result.append(f"{prefix}└── {item}")
                new_prefix = prefix + "    "
            else:
                result.append(f"{prefix}├── {item}")
                new_prefix = prefix + "│   "

            # If it's a directory, recurse
            if os.path.isdir(item_path):
                _traverse(item_path, new_prefix)

    # Start traversal from the root
    root_name = os.path.basename(os.path.abspath(project_path))
    result.append(root_name)
    _traverse(project_path, "")

    return "\n".join(result)


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
                                "filename": formatted_path,
                                "content": f"[File too large: {file_size} bytes]",
                            }
                        )
                        continue

                    # Try to read the file as text
                    with open(item_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Add file information to result
                    result.append({"filename": formatted_path, "content": content})
                except UnicodeDecodeError:
                    # For binary files, just note that
                    result.append(
                        {"filename": formatted_path, "content": "[Binary file]"}
                    )
                except (PermissionError, IsADirectoryError) as e:
                    # For files we can't read, just note that
                    result.append(
                        {
                            "filename": formatted_path,
                            "content": f"[Unable to read content: {str(e)}]",
                        }
                    )
            elif os.path.isdir(item_path):
                # Recurse into subdirectories
                _traverse(item_path)

    # Start traversal from the root
    _traverse(project_path)

    return result
