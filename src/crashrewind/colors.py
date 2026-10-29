"""ANSI color helper: the neon cyan/magenta palette, on black.

All terminal styling goes through this module. Color is switched off when the
``NO_COLOR`` environment variable is set to a non-empty value
(https://no-color.org) or when the target stream is not a TTY, so piped and
redirected output is always plain text.
"""

from __future__ import annotations

import os
import sys
from typing import TextIO

RESET = "\033[0m"

# Palette. 40 = black background; 96/95 = bright cyan/magenta; 36/35 = cyan/magenta.
STYLES = {
    "banner": "\033[1;95;40m",   # bold magenta on black: per-log headers
    "title": "\033[1;96;40m",    # bold cyan on black: finding titles
    "label": "\033[35;40m",      # magenta on black: "Why:", "Evidence:", "Try:"
    "dim": "\033[36;40m",        # cyan on black: evidence lines, metadata
    "accent": "\033[96;40m",     # bright cyan on black: fixes, rule ids
    "error": "\033[1;95;40m",    # bold magenta on black: error messages
}


def color_enabled(stream: TextIO | None = None) -> bool:
    """Return True if ANSI color should be written to ``stream`` (default stdout)."""
    if os.environ.get("NO_COLOR"):
        return False
    stream = sys.stdout if stream is None else stream
    isatty = getattr(stream, "isatty", None)
    try:
        return bool(isatty and isatty())
    except (ValueError, OSError):  # closed or detached stream
        return False


class Painter:
    """Wraps text in palette styles, or passes it through untouched when disabled."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    @classmethod
    def for_stream(cls, stream: TextIO | None = None) -> "Painter":
        return cls(color_enabled(stream))

    def paint(self, style: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"{STYLES[style]}{text}{RESET}"
