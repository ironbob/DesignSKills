from __future__ import annotations

import inspect
import json
from typing import Any


class TextPlugins:
    def upper(self, payload: str) -> str:
        return payload.upper()

    def prefix(self, payload: str, *, value: str) -> str:
        return f"{value}{payload}"


def invoke(
    plugin: object,
    method_name: str,
    payload: str,
    options: dict[str, Any],
) -> str:
    method = getattr(plugin, method_name, None)
    if not callable(method):
        raise LookupError(f"unknown plugin method: {method_name}")
    signature = inspect.signature(method)
    bound = signature.bind(payload, **options)
    return method(*bound.args, **bound.kwargs)


def handle(request: dict[str, Any]) -> dict[str, str]:
    plugin = TextPlugins()
    result = invoke(
        plugin,
        request["method"],
        request["payload"],
        request.get("options", {}),
    )
    return {"plugin": request["method"], "result": result}


if __name__ == "__main__":
    response = handle({"method": "upper", "payload": "hello"})
    print(json.dumps(response, sort_keys=True))
