"""Explicit local executable configuration; no downloads or environment changes."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = {
    "powershell": ("pwsh",),
    "freecad": ("FreeCADCmd", "freecadcmd"),
    "matlab": ("matlab",),
    "octave": ("octave-cli",),
    "scilab": ("Scilex", "scilab-cli"),
    "gmsh": ("gmsh",),
    "calculix": ("ccx",),
    "poppler": ("pdftoppm",),
}

def executable(name: str, *, required: bool = True) -> Path | None:
    """Resolve only explicit user settings or PATH; never guess a personal path."""
    if name not in COMMANDS:
        raise ValueError("Unknown local engine: " + name)
    config_path = Path(os.environ.get("CANTAX_EXECUTABLES", str(ROOT / "config/executables.local.json")))
    config = json.loads(config_path.read_text(encoding="utf-8-sig")) if config_path.is_file() else {}
    configured = os.environ.get("CANTAX_" + name.upper()) or config.get(name)
    if configured:
        if '/' not in configured and '\\' not in configured:
            found=shutil.which(configured)
            if found:
                return Path(found).resolve()
            raise FileNotFoundError(f"Configured {name} command is not on PATH: {configured}")
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            candidate = config_path.parent / candidate
        if not candidate.is_file():
            raise FileNotFoundError(f"Configured {name} executable does not exist: {candidate}")
        return candidate.resolve()
    for command in COMMANDS[name]:
        found = shutil.which(command)
        if found:
            return Path(found).resolve()
    if required:
        raise FileNotFoundError(f"{name} is unavailable. Set it in config/executables.local.json or PATH; see config/executables.example.json.")
    return None

def require_engines() -> dict[str, Path]:
    return {name: executable(name) for name in COMMANDS if name != "poppler"}

def local_engine_environment(source=None):
    """Exclude unrelated service credentials; preserve local engine/license settings."""
    source=os.environ if source is None else source
    prefixes=('OPENAI','ANTHROPIC','CODEX','CHATGPT')
    exact={'GH_TOKEN','GITHUB_TOKEN'}
    return {key:value for key,value in source.items()
            if key.upper() not in exact and not key.upper().startswith(prefixes)}
