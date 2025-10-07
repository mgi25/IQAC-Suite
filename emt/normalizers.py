"""Utilities for normalizing loosely formatted numeric input."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Union

NumberLike = Union[str, int, float, Decimal]

_DECIMAL_ALLOWED = re.compile(r"[^0-9.,+-]")
_INT_ALLOWED = re.compile(r"[^0-9+-]")


def _strip_extraneous_chars(value: str, *, allow_negative: bool) -> str:
    """Remove everything except digits, separators, and sign."""
    if not value:
        return ""
    text = value.strip().replace(" ", "")
    text = _DECIMAL_ALLOWED.sub("", text)
    if not allow_negative:
        text = text.replace("-", "")
    else:
        if text.count("-") > 1:
            text = text.replace("-", "")
        elif "-" in text and not text.startswith("-"):
            text = "-" + text.replace("-", "")
    return text


def normalize_decimal(value: Optional[NumberLike], *, allow_negative: bool = False) -> Optional[Decimal]:
    """Coerce loosely formatted numeric input into a Decimal."""
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        result = value
    else:
        text = _strip_extraneous_chars(str(value), allow_negative=allow_negative)
        if not text:
            return None
        text = text.replace(",", "")
        if text.count(".") > 1:
            head, tail = text.rsplit(".", 1)
            head = head.replace(".", "")
            text = f"{head}.{tail}"
        try:
            result = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"Unable to parse decimal value from '{value}'") from exc
    if not allow_negative and result < 0:
        raise ValueError("Negative values are not allowed")
    return result


def normalize_int(value: Optional[NumberLike], *, allow_negative: bool = False) -> Optional[int]:
    """Coerce loosely formatted numeric input into an integer."""
    if value in (None, ""):
        return None
    if isinstance(value, int):
        result = value
    else:
        text = str(value).strip().replace(" ", "")
        text = _INT_ALLOWED.sub("", text)
        if not allow_negative:
            text = text.replace("-", "")
        else:
            if text.count("-") > 1:
                text = text.replace("-", "")
            elif "-" in text and not text.startswith("-"):
                text = "-" + text.replace("-", "")
        if not text:
            return None
        try:
            result = int(float(text))
        except ValueError as exc:
            raise ValueError(f"Unable to parse integer value from '{value}'") from exc
    if not allow_negative and result < 0:
        raise ValueError("Negative values are not allowed")
    return result
