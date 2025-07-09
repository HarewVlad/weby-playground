from typing import Any

from app.utils.logger import logger


def serialize_object(obj: Any) -> dict:
    """Safely serialize objects to dictionaries."""
    if hasattr(obj, "model_dump"):
        # For newer Pydantic/OpenAI SDK versions
        return obj.model_dump()
    elif hasattr(obj, "dict"):
        # For older Pydantic/OpenAI SDK versions
        return obj.dict()
    else:
        # Fallback for other objects
        try:
            return dict(obj)
        except (TypeError, ValueError):
            logger.warning(f"Could not serialize object of type {type(obj)}")
            return {"error": "Unserializable object"}