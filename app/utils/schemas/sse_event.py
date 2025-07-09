from pydantic import BaseModel


def sse_event(data: BaseModel) -> dict:
    """Format data for Server-Sent Events."""
    return {"data": data.model_dump_json()}
