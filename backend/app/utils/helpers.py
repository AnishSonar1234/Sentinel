"""
app/utils/helpers.py
─────────────────────
Shared utility functions used across the application.
"""
import json


def parse_json_field(value: str | None, default=None):
    """Safely parse a JSON-encoded string field from the DB."""
    if default is None:
        default = []
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def encode_reasons(reasons: list[str]) -> str:
    """Encode a list of reason strings to JSON for DB storage."""
    return json.dumps(reasons)


def decode_reasons(value: str | None) -> list[str]:
    """Decode JSON-encoded reasons from DB to list."""
    return parse_json_field(value, default=[])
