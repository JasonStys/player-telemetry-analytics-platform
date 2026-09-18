"""File: privacy.py
Purpose: Pseudonymize source identifiers and reject common personal or secret-bearing payloads.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: SENSITIVE_KEY_PATTERN and VALUE_PATTERNS define conservative privacy checks.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Mapping, Sequence
from typing import Any

SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:email|phone|address|full_?name|first_?name|last_?name|token|secret|password|api_?key)",
    re.IGNORECASE,
)
VALUE_PATTERNS = (
    ("email-like value", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    (
        "phone-like value",
        re.compile(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)"),
    ),
    ("bearer credential", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE)),
)
MINIMUM_SECRET_LENGTH = 16


def pseudonymize_player_id(source_id: str, secret: str) -> str:
    """Return a stable, non-reversible player identifier using keyed SHA-256."""

    if len(secret) < MINIMUM_SECRET_LENGTH:
        raise ValueError("pseudonymization secret must contain at least 16 characters")
    digest = hmac.new(secret.encode(), source_id.encode(), hashlib.sha256).hexdigest()
    return f"ply_{digest[:12]}"


def find_privacy_violations(payload: Mapping[str, Any]) -> list[str]:
    """Walk a JSON-shaped mapping and return stable, deduplicated violation descriptions."""

    violations: set[str] = set()

    def visit(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                if SENSITIVE_KEY_PATTERN.search(str(key)):
                    violations.add(f"sensitive key at {child_path}")
                visit(child, child_path)
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
            return
        if isinstance(value, str):
            for label, pattern in VALUE_PATTERNS:
                if pattern.search(value):
                    violations.add(f"{label} at {path or '<root>'}")

    visit(payload, "")
    return sorted(violations)
