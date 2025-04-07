from smolagents import tool
import os
import re


@tool
def read_file(file_path: str) -> str:
    """Reads a file at the given path and returns its content as a string.

    Args:
        file_path: The path to the file to read.

    Returns:
        The content of the file as a string, or an error message if the operation fails.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        return content

    except FileNotFoundError:
        return f"Error: File not found at path '{file_path}'"
    except PermissionError:
        return f"Error: Permission denied when trying to read '{file_path}'"
    except Exception as e:
        return f"An unexpected error occurred while reading file: {str(e)}"


@tool
def write_file(file_path: str, content: str, mode: str = "w") -> str:
    """Writes content to a file at the given path.

    Args:
        file_path: The path to the file to write.
        content: The content to write to the file.
        mode: The write mode ('w' for overwrite, 'a' for append). Defaults to 'w'.

    Returns:
        A success message, or an error message if the operation fails.
    """
    try:
        with open(file_path, mode, encoding="utf-8") as file:
            file.write(content)

        return f"Successfully wrote to file '{file_path}'"

    except PermissionError:
        return f"Error: Permission denied when trying to write to '{file_path}'"
    except Exception as e:
        return f"An unexpected error occurred while writing to file: {str(e)}"


@tool
def create_directory(dir_path: str) -> str:
    """Creates a directory at the given path.

    Args:
        dir_path: The path where the directory should be created.

    Returns:
        A success message, or an error message if the operation fails.
    """
    try:
        os.makedirs(dir_path, exist_ok=True)
        return f"Successfully created directory at '{dir_path}'"

    except PermissionError:
        return f"Error: Permission denied when trying to create directory '{dir_path}'"
    except Exception as e:
        return f"An unexpected error occurred while creating directory: {str(e)}"


@tool
def edit_file(file_path: str, search_text: str, replace_text: str) -> str:
    """Edits a file by replacing occurrences of search_text with replace_text.

    Args:
        file_path: The path to the file to edit.
        search_text: The text to search for.
        replace_text: The text to replace with.

    Returns:
        A success message with the number of replacements, or an error message if the operation fails.
    """
    try:
        # Read the file content
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Perform the replacement
        new_content, count = re.subn(search_text, replace_text, content)

        # Write the modified content back to the file
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(new_content)

        return f"Successfully edited file '{file_path}' ({count} replacements made)"

    except FileNotFoundError:
        return f"Error: File not found at path '{file_path}'"
    except PermissionError:
        return f"Error: Permission denied when trying to edit '{file_path}'"
    except Exception as e:
        return f"An unexpected error occurred while editing file: {str(e)}"


@tool
def list_directory(dir_path: str) -> str:
    """Lists the contents of a directory at the given path.

    Args:
        dir_path: The path to the directory to list.

    Returns:
        A string containing the directory contents, or an error message if the operation fails.
    """
    try:
        items = os.listdir(dir_path)

        # Categorize items as files or directories
        files = []
        directories = []

        for item in items:
            item_path = os.path.join(dir_path, item)
            if os.path.isdir(item_path):
                directories.append(f"{item}/")
            else:
                files.append(item)

        # Sort alphabetically
        directories.sort()
        files.sort()

        # Format the output
        output = f"Contents of '{dir_path}':\n\n"

        if directories:
            output += "Directories:\n"
            output += "\n".join(f"- {d}" for d in directories)
            output += "\n\n"

        if files:
            output += "Files:\n"
            output += "\n".join(f"- {f}" for f in files)

        return output

    except FileNotFoundError:
        return f"Error: Directory not found at path '{dir_path}'"
    except PermissionError:
        return f"Error: Permission denied when trying to list directory '{dir_path}'"
    except Exception as e:
        return f"An unexpected error occurred while listing directory: {str(e)}"


@tool
def search_file(file_path: str, search_pattern: str) -> str:
    """Searches for a pattern in a file and returns matching lines with line numbers.

    Args:
        file_path: The path to the file to search.
        search_pattern: The regex pattern to search for.

    Returns:
        A string containing the matching lines with line numbers, or an error message if the operation fails.
    """
    try:
        matches = []
        pattern = re.compile(search_pattern)

        with open(file_path, "r", encoding="utf-8") as file:
            for line_num, line in enumerate(file, 1):
                if pattern.search(line):
                    matches.append((line_num, line.strip()))

        if matches:
            result = f"Found {len(matches)} matches in '{file_path}':\n\n"
            for line_num, line in matches:
                result += f"Line {line_num}: {line}\n"
            return result
        else:
            return f"No matches found for '{search_pattern}' in '{file_path}'"

    except FileNotFoundError:
        return f"Error: File not found at path '{file_path}'"
    except PermissionError:
        return f"Error: Permission denied when trying to read '{file_path}'"
    except re.error as e:
        return f"Error in regex pattern: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred while searching file: {str(e)}"


filesystem_tools = [
    read_file,
    write_file,
    create_directory,
    # edit_file,
    list_directory,
    search_file,
]
