import json
from typing import Any, Optional
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


def normalize_json_payload(data: Any) -> Optional[Any]:
    """Normalize payloads destined for JSON columns.

    - Accepts dict/list directly
    - If a string is provided, attempts to parse JSON
    - Returns None when invalid or non-serializable
    """
    if data is None:
        return None

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return None

    try:
        primitive = _serialize(data)
        json.dumps(primitive, ensure_ascii=False)
        return primitive
    except Exception:
        return None