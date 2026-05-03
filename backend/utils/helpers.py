"""Utility helpers for the Anime AI Agent."""

import hashlib
import re
import time


def generate_id(prefix: str = "proj") -> str:
    """Generate a unique project ID."""
    ts = str(time.time()).encode()
    return f"{prefix}_{hashlib.md5(ts).hexdigest()[:10]}"


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name.lower().strip("_")[:60]


def format_duration(seconds: float) -> str:
    """Format seconds into MM:SS."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"
