"""Explain Proton/Wine crash logs with rule-based diagnostics."""

# Single source of truth for the project name. If you rename the project,
# change it here and follow RENAME.md for the remaining places.
NAME = "Crashrewind"
# Command / package / distribution name, derived so NAME stays the only literal.
PROG = NAME.lower()
__version__ = "0.1.0"

from .analyzer import Finding, analyze_text  # noqa: E402
from .rules import RULES, Rule  # noqa: E402

__all__ = ["NAME", "PROG", "__version__", "Finding", "Rule", "RULES", "analyze_text"]
