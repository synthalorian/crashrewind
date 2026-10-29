"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from . import NAME, PROG, __version__
from .analyzer import Finding, analyze_text
from .colors import Painter
from .rules import RULES


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _format_text(source: str, findings: list[Finding], p: Painter) -> str:
    out = [p.paint("banner", f"== {source}")]
    if not findings:
        out.append(p.paint("title", "No known problems detected."))
        out.append(p.paint("dim", "Tip: run the game with PROTON_LOG=1 %command% to get a fuller log "
                                  "(written to ~/steam-<appid>.log)."))
        return "\n".join(out)
    for i, f in enumerate(findings, start=1):
        out.append("")
        meta = f"({f.rule.severity}, {f.hits} hit{'s' if f.hits != 1 else ''})"
        out.append(f"{p.paint('title', f'[{i}] {f.rule.title}')}  {p.paint('dim', meta)}")
        out.append(f"    {p.paint('label', 'Why:')} {f.rule.cause}")
        out.append(f"    {p.paint('label', 'Evidence:')}")
        for lineno, text in f.evidence:
            out.append(p.paint("dim", f"      L{lineno}: {text}"))
        out.append(f"    {p.paint('label', 'Try:')}")
        for fix in f.fixes:
            out.append(f"      - {p.paint('accent', fix)}")
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Explain Proton/Wine crash logs and suggest fixes.",
    )
    parser.add_argument("--version", action="version", version=f"{NAME} {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    an = sub.add_parser("analyze", help="analyze one or more log files ('-' for stdin)")
    an.add_argument("logs", nargs="+", metavar="LOG")
    an.add_argument("--json", action="store_true", help="emit JSON instead of text")
    an.add_argument("--fail-on-findings", action="store_true",
                    help="exit with status 1 if any problem is detected")

    sub.add_parser("rules", help="list the built-in diagnostic rules")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "rules":
        p = Painter.for_stream(sys.stdout)
        for rule in RULES:
            print(f"{p.paint('accent', f'{rule.id:<16}')} {p.paint('dim', f'{rule.severity:<7}')} {rule.title}")
        return 0

    results: dict[str, list[Finding]] = {}
    for path in args.logs:
        try:
            results[path] = analyze_text(_read(path))
        except OSError as exc:
            err = Painter.for_stream(sys.stderr)
            print(err.paint("error", f"{PROG}: cannot read {path}: {exc.strerror or exc}"), file=sys.stderr)
            return 2

    if args.json:
        payload = {p: [f.to_dict() for f in fs] for p, fs in results.items()}
        print(json.dumps(payload, indent=2))
    else:
        p = Painter.for_stream(sys.stdout)
        print("\n\n".join(_format_text(path, fs, p) for path, fs in results.items()))

    if args.fail_on_findings and any(results.values()):
        return 1
    return 0
