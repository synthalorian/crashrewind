"""Rule definitions: regex patterns mapped to likely causes and fixes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# DLLs that come from the Visual C++ redistributable. Handled by the vcrun rule
# so the generic missing-DLL rule does not report them twice.
VCRUN_DLLS = {
    "vcruntime140.dll": "vcrun2022",
    "vcruntime140_1.dll": "vcrun2022",
    "msvcp140.dll": "vcrun2022",
    "msvcp140_1.dll": "vcrun2022",
    "msvcp140_2.dll": "vcrun2022",
    "concrt140.dll": "vcrun2022",
    "vcomp140.dll": "vcrun2022",
    "msvcr120.dll": "vcrun2013",
    "msvcp120.dll": "vcrun2013",
    "msvcr110.dll": "vcrun2012",
    "msvcp110.dll": "vcrun2012",
    "msvcr100.dll": "vcrun2010",
    "msvcp100.dll": "vcrun2010",
    "msvcr90.dll": "vcrun2008",
    "msvcp90.dll": "vcrun2008",
}

# Known winetricks verbs for commonly missing non-vcrun DLLs.
DLL_VERBS = {
    "d3dcompiler_43.dll": "d3dcompiler_43",
    "d3dcompiler_47.dll": "d3dcompiler_47",
    "d3dx9_43.dll": "d3dx9",
    "d3dx11_43.dll": "d3dx11_43",
    "xaudio2_7.dll": "xact",
    "x3daudio1_7.dll": "xact",
    "xinput1_3.dll": "xinput",
    "physxloader.dll": "physx",
    "mfplat.dll": "mf",
    "mf.dll": "mf",
    "wmvcore.dll": "wmp11",
    "quartz.dll": "quartz",
    "faudio.dll": "faudio",
}


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    severity: str
    patterns: tuple[re.Pattern[str], ...]
    cause: str
    fixes: tuple[str, ...]
    # Optional: given the regex matches, return extra fix lines (e.g. per-DLL).
    extra_fixes: Callable[[list[re.Match[str]]], list[str]] | None = field(
        default=None, compare=False
    )
    # Optional: return False to drop a match (e.g. to defer to a more specific rule).
    accept: Callable[[re.Match[str]], bool] | None = field(default=None, compare=False)


def _p(*regexes: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(r, re.IGNORECASE) for r in regexes)


_DLL_NOT_FOUND = r"import_dll Library (?P<dll>[\w.\-]+\.dll) \(which is needed by .*\) not found"


def _dll(m: re.Match[str]) -> str:
    return m.group("dll").lower()


def _missing_dll_fixes(matches: list[re.Match[str]]) -> list[str]:
    out = []
    for dll in sorted({_dll(m) for m in matches if "dll" in m.groupdict()}):
        verb = DLL_VERBS.get(dll)
        if verb:
            out.append(f"{dll}: protontricks <appid> {verb}")
        else:
            out.append(f"{dll}: check the game's install for a bundled redistributable "
                       "or search winetricks for a matching verb")
    return out


def _vcrun_fixes(matches: list[re.Match[str]]) -> list[str]:
    verbs = sorted({VCRUN_DLLS[_dll(m)] for m in matches
                    if "dll" in m.groupdict() and _dll(m) in VCRUN_DLLS})
    return [f"protontricks <appid> {v}" for v in verbs]


RULES: tuple[Rule, ...] = (
    Rule(
        id="anticheat",
        title="Anti-cheat refused to start",
        severity="high",
        patterns=_p(
            r"EasyAntiCheat.*\b(?:fail|error|not installed|untrusted)",
            r"\bEAC\b.*\b(?:launch error|failed to initiali[sz]e)",
            r"BattlEye.*\b(?:fail|error|not running|could not)",
            r"BEService.*\b(?:fail|error|not running)",
            r"\b(?:vgk|vanguard|nprotect|gameguard|xigncode)\b.*\b(?:fail|error|not)\b",
        ),
        cause=(
            "The game's anti-cheat did not initialise. Kernel-level anti-cheats "
            "(Vanguard, some GameGuard/XIGNCODE titles) cannot run under Wine at all; "
            "EAC and BattlEye only work if the developer enabled Proton support."
        ),
        fixes=(
            "Check areweanticheatyet.com for the game's current status.",
            "Use Proton 7.0 or newer (EAC/BattlEye runtimes ship as Steam tools).",
            "Install 'Proton EasyAntiCheat Runtime' / 'Proton BattlEye Runtime' from the Steam library (Tools).",
            "If the developer has not enabled Linux support, there is no client-side fix.",
        ),
    ),
    Rule(
        id="vulkan-dxvk",
        title="Vulkan / DXVK initialisation failure",
        severity="high",
        patterns=_p(
            r"DxvkInstance: Failed to create Vulkan",
            r"vkCreateInstance failed",
            r"VK_ERROR_INITIALIZATION_FAILED",
            r"VK_ERROR_INCOMPATIBLE_DRIVER",
            r"VK_ERROR_DEVICE_LOST",
            r"VK_ERROR_OUT_OF_DEVICE_MEMORY",
            r"Required Vulkan extension .* not supported",
            r"DXVK: No adapters found",
            r"vkd3d.*(?:Failed to create|no suitable) .*device",
            r"Failed to load vulkan-1\.dll|could not load vulkan",
        ),
        cause=(
            "DXVK/VKD3D could not get a usable Vulkan device. Usually a missing or "
            "outdated Vulkan driver, a missing 32-bit driver, the wrong GPU being "
            "picked, or (for DEVICE_LOST) a GPU hang/driver crash."
        ),
        fixes=(
            "Run `vulkaninfo --summary` and confirm your GPU is listed.",
            "Install the 32-bit Vulkan driver too (e.g. lib32-vulkan-radeon / lib32-nvidia-utils / mesa-vulkan-drivers:i386).",
            "Update Mesa or the NVIDIA driver; DXVK 2.x needs Vulkan 1.3.",
            "On hybrid graphics, try DXVK_FILTER_DEVICE_NAME=\"<gpu>\" or prime-run.",
            "As a fallback, launch with PROTON_USE_WINED3D=1 %command% (slower, OpenGL).",
        ),
    ),
    Rule(
        id="esync-fsync",
        title="esync/fsync limit or support problem",
        severity="medium",
        patterns=_p(
            r"esync.*Too many open files",
            r"eventfd.*Too many open files",
            r"err:esync",
            r"fsync.*(?:futex_waitv|futex2) (?:is )?not supported",
            r"err:fsync",
            r"Failed to create (?:esync|fsync) object",
        ),
        cause=(
            "esync needs a high open-file limit (RLIMIT_NOFILE), and fsync needs a "
            "kernel with futex_waitv (5.16+). When the limit is too low or the "
            "kernel lacks support, sync objects fail and the game hangs or crashes."
        ),
        fixes=(
            "Check `ulimit -Hn`; it should be at least 524288.",
            "Raise it via DefaultLimitNOFILE=1048576 in /etc/systemd/system.conf and user.conf, then reboot.",
            "Test without them: PROTON_NO_ESYNC=1 PROTON_NO_FSYNC=1 %command%",
        ),
    ),
    Rule(
        id="dotnet",
        title=".NET runtime missing",
        severity="high",
        patterns=_p(
            r"Wine Mono is not installed",
            r"err:mscoree:.*(?:not installed|failed|could not)",
            r"CLR error: 80004005",
            r"System\.IO\.FileNotFoundException:.*(?:System\.|mscorlib)",
            r"This application requires (?:the )?\.NET",
            r"import_dll Library mscoree\.dll .* not found",
        ),
        cause=(
            "The program (or its launcher) needs the .NET Framework and neither "
            "Wine Mono nor a native .NET runtime is available in the prefix."
        ),
        fixes=(
            "Let Proton recreate the prefix (delete compatdata/<appid>) so Wine Mono is installed.",
            "If Mono is not enough: protontricks <appid> dotnet48",
            "For .NET 6+ apps install the desktop runtime: protontricks <appid> dotnetdesktop6",
        ),
    ),
    Rule(
        id="vcrun",
        title="Visual C++ runtime missing",
        severity="high",
        patterns=_p(_DLL_NOT_FOUND),
        accept=lambda m: _dll(m) in VCRUN_DLLS,
        cause=(
            "The game links against the Microsoft Visual C++ redistributable, "
            "which is not installed in the Wine prefix."
        ),
        fixes=("Install the matching runtime with protontricks:",),
        extra_fixes=_vcrun_fixes,
    ),
    Rule(
        id="missing-dll",
        title="Required DLL not found",
        severity="high",
        patterns=_p(_DLL_NOT_FOUND),
        accept=lambda m: _dll(m) not in VCRUN_DLLS and _dll(m) != "mscoree.dll",
        cause=(
            "The executable imports a DLL that is not present in the game folder "
            "or the Wine prefix, so the loader aborts before the game starts."
        ),
        fixes=("Install the providing component:",),
        extra_fixes=_missing_dll_fixes,
    ),
    Rule(
        id="ntdll-pagefault",
        title="Unhandled page fault (access violation)",
        severity="medium",
        patterns=_p(
            r"Unhandled page fault on (?:read|write|execute) access to (?P<addr>[0-9a-fx]+)",
            r"Unhandled exception: page fault on (?:read|write|execute) access",
            r"Unhandled exception 0xc0000005",
            r"err:seh:.*(?:c0000005|EXCEPTION_ACCESS_VIOLATION)",
            r"EXCEPTION_ACCESS_VIOLATION",
        ),
        cause=(
            "The process crashed with an access violation. Null-pointer reads "
            "(address 0) are often a side effect of an earlier failure in the log "
            "(missing DLL, failed device creation); otherwise it can be a "
            "game bug, a broken mod, or a regression in this Proton version."
        ),
        fixes=(
            "Fix any other findings above first; they are frequently the root cause.",
            "Try a different Proton version (Experimental, GE-Proton, or an older stable).",
            "Verify game files in Steam and disable mods/overlays (MANGOHUD, Steam overlay).",
            "Try PROTON_USE_WINED3D=1 or PROTON_NO_ESYNC=1 to rule out graphics/sync layers.",
        ),
    ),
)


def get_rule(rule_id: str) -> Rule:
    for rule in RULES:
        if rule.id == rule_id:
            return rule
    raise KeyError(rule_id)
