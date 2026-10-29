import io

import pytest

from crashrewind import PROG, cli
from crashrewind.colors import RESET, STYLES, Painter, color_enabled


class FakeTTY(io.StringIO):
    def isatty(self) -> bool:
        if self.closed:
            raise ValueError("I/O operation on closed file.")
        return True


@pytest.fixture(autouse=True)
def _clear_no_color(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)


def test_enabled_on_tty():
    assert color_enabled(FakeTTY()) is True


def test_disabled_when_not_a_tty():
    assert color_enabled(io.StringIO()) is False


def test_disabled_by_no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert color_enabled(FakeTTY()) is False


def test_empty_no_color_is_ignored(monkeypatch):
    # https://no-color.org: only a non-empty value disables color.
    monkeypatch.setenv("NO_COLOR", "")
    assert color_enabled(FakeTTY()) is True


def test_disabled_on_closed_stream():
    stream = FakeTTY()
    stream.close()
    assert color_enabled(stream) is False


def test_painter_passthrough_when_disabled():
    assert Painter(False).paint("title", "hello") == "hello"


def test_painter_wraps_when_enabled():
    assert Painter(True).paint("title", "hello") == f"{STYLES['title']}hello{RESET}"


def test_palette_is_cyan_magenta_on_black():
    for code in STYLES.values():
        params = code[2:-1].split(";")
        assert "40" in params  # black background
        assert any(p in params for p in ("35", "36", "95", "96"))  # magenta/cyan


def _run(monkeypatch, stdout, argv):
    monkeypatch.setattr(cli.sys, "stdout", stdout)
    cli.main(argv)
    return stdout.getvalue()


def test_cli_plain_when_piped(monkeypatch, fixtures_dir):
    out = _run(monkeypatch, io.StringIO(), ["analyze", str(fixtures_dir / "anticheat.log")])
    assert "\033[" not in out
    assert "Anti-cheat refused to start" in out


def test_cli_plain_with_no_color_on_tty(monkeypatch, fixtures_dir):
    monkeypatch.setenv("NO_COLOR", "1")
    out = _run(monkeypatch, FakeTTY(), ["analyze", str(fixtures_dir / "anticheat.log")])
    assert "\033[" not in out


def test_cli_rules_plain_with_no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert "\033[" not in _run(monkeypatch, FakeTTY(), ["rules"])


def test_cli_colored_on_tty(monkeypatch, fixtures_dir):
    out = _run(monkeypatch, FakeTTY(), ["analyze", str(fixtures_dir / "anticheat.log")])
    assert STYLES["title"] in out and RESET in out


def test_json_never_colored(monkeypatch, fixtures_dir):
    import json

    out = _run(monkeypatch, FakeTTY(), ["analyze", "--json", str(fixtures_dir / "anticheat.log")])
    assert "\033[" not in out
    json.loads(out)


def test_error_plain_when_stderr_not_tty(monkeypatch, tmp_path):
    err = io.StringIO()
    monkeypatch.setattr(cli.sys, "stderr", err)
    assert cli.main(["analyze", str(tmp_path / "nope.log")]) == 2
    assert "\033[" not in err.getvalue()
    assert err.getvalue().startswith(f"{PROG}: cannot read")
