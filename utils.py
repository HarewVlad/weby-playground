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
