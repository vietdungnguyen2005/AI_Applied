import json
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

SCHEMA = json.loads(files("vmarket_ai.gateway").joinpath("wire.json").read_text(encoding="utf-8"))


class GatewayError(RuntimeError):
    def __init__(self, code: str, status: int) -> None:
        self.code, self.status = code, status
        super().__init__(code)


def validate(name: str, value: Any) -> None:
    validator = Draft202012Validator(
        {**SCHEMA, "$ref": f"#/$defs/{name}"}, format_checker=FormatChecker()
    )
    if not validator.is_valid(value):
        raise GatewayError("INPUT_INVALID", 400)


def strict_json(raw: bytes | str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON member")
            result[key] = value
        return result

    try:
        return json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (ValueError, UnicodeError):
        raise GatewayError("INPUT_INVALID", 400) from None
