"""Navigation-related template helpers."""

from __future__ import annotations

import re
from typing import Iterable, List

from django import template

register = template.Library()


def _flatten_names(names: Iterable[str]) -> List[str]:
    tokens: List[str] = []
    for name in names:
        if isinstance(name, (list, tuple, set)):
            tokens.extend(_flatten_names(name))
        elif name:
            tokens.extend(
                token
                for token in re.split(r"[\s,]+", str(name).strip())
                if token
            )
    return tokens


@register.simple_tag
def url_in(current_url: str | None, *names) -> bool:
    """Return True if ``current_url`` matches any of the provided names."""

    if not current_url:
        return False

    candidates = _flatten_names(names)
    return str(current_url) in candidates
