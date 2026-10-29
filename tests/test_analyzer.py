import pytest

from crashrewind import RULES, analyze_text
from crashrewind.rules import get_rule


def ids(findings):
    return [f.rule.id for f in findings]


@pytest.mark.parametrize(
    "log, expected",
    [
        ("missing_dlls.log", {"vcrun", "missing-dll"}),
        ("dxvk_vulkan.log", {"vulkan-dxvk", "ntdll-pagefault"}),
        ("esync_limits.log", {"esync-fsync"}),
        ("ntdll_pagefault.log", {"ntdll-pagefault"}),
        ("dotnet_missing.log", {"dotnet"}),
        ("anticheat.log", {"anticheat"}),
        ("clean.log", set()),
    ],
)
def test_fixture_findings(fixture_text, log, expected):
    assert set(ids(analyze_text(fixture_text(log)))) == expected


def test_vcrun_dlls_not_double_reported(fixture_text):
    findings = {f.rule.id: f for f in analyze_text(fixture_text("missing_dlls.log"))}
    vcrun_evidence = " ".join(t for _, t in findings["vcrun"].evidence)
    dll_evidence = " ".join(t for _, t in findings["missing-dll"].evidence)
    assert "VCRUNTIME140.dll" in vcrun_evidence and "MSVCP140.dll" in vcrun_evidence
    assert "VCRUNTIME140" not in dll_evidence
    assert "d3dcompiler_47.dll" in dll_evidence


def test_dll_specific_fixes_use_appid(fixture_text):
    findings = {f.rule.id: f for f in analyze_text(fixture_text("missing_dlls.log"))}
    assert "protontricks 1145360 vcrun2022" in findings["vcrun"].fixes
    assert any("protontricks 1145360 d3dcompiler_47" in fx for fx in findings["missing-dll"].fixes)
    assert not any("<appid>" in fx for f in findings.values() for fx in f.fixes)


def test_appid_placeholder_kept_without_header():
    log = 'err:module:import_dll Library msvcp140.dll (which is needed by L"C:\\\\a.exe") not found'
    (finding,) = analyze_text(log)
    assert "protontricks <appid> vcrun2022" in finding.fixes


def test_high_severity_sorted_first(fixture_text):
    findings = analyze_text(fixture_text("dxvk_vulkan.log"))
    assert ids(findings)[0] == "vulkan-dxvk"


def test_evidence_line_numbers_point_at_matches(fixture_text):
    text = fixture_text("esync_limits.log")
    lines = text.splitlines()
    (finding,) = analyze_text(text)
    for lineno, snippet in finding.evidence:
        assert lines[lineno - 1].strip() == snippet
    assert finding.hits == 5


def test_up_and_running_is_not_a_problem():
    assert analyze_text("esync: up and running.\nfsync: up and running.\n") == []


def test_eac_pattern_does_not_match_inside_words():
    assert analyze_text("info: reached the end, nothing failed here\n") == []


def test_rule_ids_unique_and_severities_valid():
    rule_ids = [r.id for r in RULES]
    assert len(rule_ids) == len(set(rule_ids))
    assert all(r.severity in {"high", "medium", "low"} for r in RULES)
    assert get_rule("dotnet").title


def test_get_rule_unknown():
    with pytest.raises(KeyError):
        get_rule("nope")
