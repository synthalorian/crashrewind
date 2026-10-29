# Crashrewind

**Your game flatlined under Proton. The log is 40,000 lines of `fixme:` static. Crashrewind rewinds the tape so you don't have to.**

Crashrewind cruises through Proton/Wine logs looking for the handful of
failures behind most Linux crashes, tells you *why* in plain English, and
hands you the exact command to try next — with your game's Steam app id
already dialed in.

```
$ crashrewind analyze ~/steam-1145360.log

[1] Visual C++ runtime missing  (high, 2 hits)
    Why: The game links against the Microsoft Visual C++ redistributable, ...
    Evidence:
      L16: err:module:import_dll Library VCRUNTIME140.dll (...) not found
    Try:
      - protontricks 1145360 vcrun2022
```

No dependencies, no network, no telemetry. Just Python 3.10+, regexes, and a
neon glow.

## What it detects

| Rule id           | Catches                                                                    |
|-------------------|----------------------------------------------------------------------------|
| `missing-dll`     | `import_dll ... not found` (with winetricks verbs for d3dcompiler, xact, …) |
| `vcrun`           | Missing `VCRUNTIME140` / `MSVCP140` / older MSVC runtimes                  |
| `dotnet`          | Wine Mono not installed, `mscoree` failures, .NET exceptions               |
| `vulkan-dxvk`     | DXVK/VKD3D can't create a Vulkan instance/device, `VK_ERROR_*`             |
| `esync-fsync`     | `Too many open files`, missing `futex_waitv`                               |
| `ntdll-pagefault` | Unhandled page faults / `c0000005` access violations                       |
| `anticheat`       | EasyAntiCheat / BattlEye / kernel anti-cheat launch failures               |

Run `crashrewind rules` to scroll the full lineup from the CLI.

## Usage

First, capture the signal: set the game's Steam launch options to

```
PROTON_LOG=1 %command%
```

and Proton writes `~/steam-<appid>.log`. Then hit play:

```sh
crashrewind analyze ~/steam-1145360.log          # human-readable report
crashrewind analyze --json a.log b.log           # machine-readable, multiple files
cat wine.log | crashrewind analyze -             # read from stdin
crashrewind analyze --fail-on-findings x.log     # exit 1 if anything was found
python3 -m crashrewind analyze x.log             # without installing the script
```

Exit codes: `0` success, `1` findings present (only with `--fail-on-findings`),
`2` a log could not be read.

### Colors

On a terminal the report glows cyan and magenta on black. The neon switches
off automatically when:

- the `NO_COLOR` environment variable is set to any non-empty value
  ([no-color.org](https://no-color.org)), or
- output isn't a TTY (piped, redirected, captured by CI).

`--json` output is never colored. All styling lives in
`src/crashrewind/colors.py`.

## Install

```sh
pip install .
```

## Development

Layout: `src/crashrewind/` (package), `tests/` (pytest), `tests/fixtures/` (sample logs).

```sh
python3 -m pytest -q        # works from the repo root without installing
```

Adding a rule: append a `Rule` to `RULES` in `src/crashrewind/rules.py`, drop a
realistic log in `tests/fixtures/`, and add it to the parametrized test in
`tests/test_analyzer.py`. Tests never touch the network.

Renaming the project: see [RENAME.md](RENAME.md).

## License

MIT — see [LICENSE](LICENSE).
