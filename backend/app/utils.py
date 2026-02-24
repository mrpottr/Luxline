"""General utility helpers shared across backend modules."""

import re


def slugify(value: str) -> str:
    """Convert free-form text into a URL-friendly slug."""
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")
