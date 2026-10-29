import io
import json
import subprocess
import sys

from crashrewind import NAME, PROG, __version__
from crashrewind.cli import main


def test_version(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert f"{NAME} {__version__}" in capsys.readouterr().out


def test_rules_lists_all(capsys):
    assert main(["rules"]) == 0
    out = capsys.readouterr().out
    for rule_id in ("anticheat", "vulkan-dxvk", "esync-fsync", "dotnet", "vcrun", "missing-dll"):
        assert rule_id in out


def test_analyze_text_output(capsys, fixtures_dir):
    assert main(["analyze", str(fixtures_dir / "anticheat.log")]) == 0
    out = capsys.readouterr().out
    assert "Anti-cheat refused to start" in out
    assert "Untrusted system file" in out
    assert "Try:" in out


def test_analyze_clean_log(capsys, fixtures_dir):
    assert main(["analyze", "--fail-on-findings", str(fixtures_dir / "clean.log")]) == 0
    assert "No known problems detected." in capsys.readouterr().out


def test_fail_on_findings(fixtures_dir):
    assert main(["analyze", "--fail-on-findings", str(fixtures_dir / "dotnet_missing.log")]) == 1


def test_json_multiple_files(capsys, fixtures_dir):
    a = str(fixtures_dir / "dotnet_missing.log")
    b = str(fixtures_dir / "clean.log")
    assert main(["analyze", "--json", a, b]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[b] == []
    assert data[a][0]["id"] == "dotnet"
    assert data[a][0]["evidence"][0]["line"] > 0


def test_stdin(capsys, monkeypatch, fixture_text):
    monkeypatch.setattr(sys, "stdin", io.StringIO(fixture_text("esync_limits.log")))
    assert main(["analyze", "-"]) == 0
    assert "esync/fsync" in capsys.readouterr().out


def test_missing_file(capsys, tmp_path):
    assert main(["analyze", str(tmp_path / "nope.log")]) == 2
    assert "cannot read" in capsys.readouterr().err


def test_module_entrypoint(fixtures_dir):
    import os
    from pathlib import Path

    env = dict(os.environ)
    src = str(Path(__file__).resolve().parent.parent / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", PROG, "analyze", str(fixtures_dir / "ntdll_pagefault.log")],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert proc.returncode == 0
    assert "page fault" in proc.stdout
