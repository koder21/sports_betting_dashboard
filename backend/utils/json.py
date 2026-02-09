import json
from typing import Any
from datetime import datetime


def _serialize(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    return obj


def safe_json(data: Any) -> str:
    try:
        return json.dumps(_serialize(data), ensure_ascii=False)
    except Exception:
        return "{}"


def to_primitive(data: Any) -> Any:
    """Convert objects (datetimes, lists, dicts) into JSON-serializable primitives.

    Returns the transformed structure (not a JSON string).
    """
    return _serialize(data)