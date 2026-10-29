"""Match a log against the rule set and collect findings."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .rules import RULES, SEVERITY_ORDER, Rule

MAX_EVIDENCE = 5
APPID_RE = re.compile(r"^SteamGameId:\s*(\d+)", re.MULTILINE)


@dataclass
class Finding:
    rule: Rule
    hits: int = 0
    evidence: list[tuple[int, str]] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.rule.id,
            "title": self.rule.title,
            "severity": self.rule.severity,
            "hits": self.hits,
            "cause": self.rule.cause,
            "fixes": self.fixes,
            "evidence": [{"line": n, "text": t} for n, t in self.evidence],
        }


def analyze_text(text: str, rules: tuple[Rule, ...] = RULES) -> list[Finding]:
    """Return findings for *text*, most severe (then most frequent) first."""
    lines = text.splitlines()
    appid_match = APPID_RE.search(text)
    findings: list[Finding] = []
    for rule in rules:
        matches: list[re.Match[str]] = []
        finding = Finding(rule)
        for lineno, line in enumerate(lines, start=1):
            for pattern in rule.patterns:
                m = pattern.search(line)
                if m and (rule.accept is None or rule.accept(m)):
                    matches.append(m)
                    finding.hits += 1
                    if len(finding.evidence) < MAX_EVIDENCE:
                        finding.evidence.append((lineno, line.strip()))
                    break
        if not matches:
            continue
        finding.fixes = list(rule.fixes)
        if rule.extra_fixes:
            finding.fixes += rule.extra_fixes(matches)
        if appid_match:
            finding.fixes = [f.replace("<appid>", appid_match.group(1)) for f in finding.fixes]
        findings.append(finding)
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.rule.severity], -f.hits))
    return findings
