import re


def check_for_complete_edit_tags(content):
    """
    Check if the accumulated content contains complete <Edit>...</Edit> tags.
    Returns True if there are complete tags that can be processed.
    """
    # Simple check for complete Edit tags
    edit_pattern = re.compile(r'<Edit\s+filename="[^"]+"\s*>.*?</Edit>', re.DOTALL | re.IGNORECASE)
    return bool(edit_pattern.search(content))
