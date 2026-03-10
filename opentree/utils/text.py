"""
Text utilities for OpenTree.
"""

from datetime import datetime
from typing import Optional


def safe_decode(data: bytes, encoding: str = "utf-8") -> str:
    """
    Safely decode bytes to string with fallback encoding.
    
    Tries the specified encoding first, then latin-1 as fallback.
    """
    try:
        return data.decode(encoding)
    except UnicodeDecodeError:
        try:
            return data.decode("latin-1")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")


def truncate(text: str, max_length: int = 80, suffix: str = "...") -> str:
    """Truncate text to max_length characters with suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_timestamp(ts: datetime | float | int | str) -> str:
    """Format a timestamp for display."""
    if isinstance(ts, (int, float)):
        dt = datetime.fromtimestamp(ts)
    elif isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            return ts
    else:
        dt = ts
    
    return dt.strftime("%Y-%m-%d %H:%M")


def format_bytes(size: int) -> str:
    """Format byte size for display."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def first_line(text: str) -> str:
    """Get the first line of text."""
    return text.split("\n", 1)[0]


def word_wrap(text: str, width: int = 72) -> str:
    """Wrap text at word boundaries."""
    lines = []
    for paragraph in text.split("\n"):
        if len(paragraph) <= width:
            lines.append(paragraph)
            continue
        
        words = paragraph.split()
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(" ".join(current_line))
    
    return "\n".join(lines)
