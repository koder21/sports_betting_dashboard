import asyncio
from typing import Any


async def safe_sleep(seconds: float = 0.2) -> None:
    await asyncio.sleep(seconds)


def safe_get(d: dict, path: list[str], default: Any = None) -> Any:
    cur = d
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur

__all__ = ["safe_sleep", "safe_get"]