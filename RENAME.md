# Renaming the project

The runtime name lives in **one constant**: `NAME` in `src/crashrewind/__init__.py`
(the display name, e.g. `Crashrewind`). `PROG = NAME.lower()` is derived from it
and is the CLI command / package name. The CLI's `prog`, `--version` output,
error prefixes and the `python -m` test all read these. Packaging metadata, the
import path and docs can't import Python, so they repeat the name literally.
Every occurrence is listed below (verified with
`grep -rniI crashrewind --exclude-dir=.git .`).

## Source of truth

| File | Line(s) | What |
|------|---------|------|
| `src/crashrewind/__init__.py` | 5 | `NAME = "Crashrewind"` (display name; `PROG` on line 7 derives from it) |

## Package / import path

| Place | What |
|-------|------|
| `src/crashrewind/` | Package directory name (rename the directory) |
| `pyproject.toml` | 6: `name = "crashrewind"` (distribution name) |
| `pyproject.toml` | 25: `crashrewind = "crashrewind.cli:main"` (console script name and module path) |
| `pyproject.toml` | 28: `attr = "crashrewind.__version__"` |
| `tests/test_analyzer.py` | 3–4: `from crashrewind ...` imports |
| `tests/test_cli.py` | 6–7: `from crashrewind ...` imports |
| `tests/test_colors.py` | 5–6: `from crashrewind ...` imports |

## CI

| File | Line(s) | What |
|------|---------|------|
| `.github/workflows/ci.yml` | 26–27 | Smoke test calls the `crashrewind` console script |

## Documentation

| File | Line(s) | What |
|------|---------|------|
| `README.md` | 1, 3, 5, 11, 36, 49–53, 69, 79, 85 | Title, pitch, usage examples, colors, layout and rule-adding notes |
| `RENAME.md` | throughout | This file |

## Outside the tree

- The repository / working directory name (`crashrewind/`).
- Any generated `*.egg-info/` or `build/` directories (gitignored; delete and rebuild).

## Quick rename

The display name is capitalized, so replace both spellings:

```sh
OLD=crashrewind NEW=newname
OLD_DISPLAY=Crashrewind NEW_DISPLAY=Newname
mv src/$OLD src/$NEW
grep -rlI "$OLD_DISPLAY" --exclude-dir=.git . | xargs -r sed -i "s/$OLD_DISPLAY/$NEW_DISPLAY/g"
grep -rlI "$OLD" --exclude-dir=.git . | xargs -r sed -i "s/$OLD/$NEW/g"
grep -rniI "$OLD" --exclude-dir=.git .   # should print nothing
python3 -m pytest -q
```
