"""Portable runtime configuration for the PPA3 local environment."""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
DEFAULT_LOCAL_ROOT = Path(r"C:\PPA3Testing")


def local_root():
    return Path(os.environ.get("PPA3_LOCAL_ROOT", str(DEFAULT_LOCAL_ROOT))).expanduser().resolve()


def local_config_dir():
    explicit = os.environ.get("PPA3_LOCAL_CONFIG")
    return Path(explicit).expanduser().resolve() if explicit else local_root() / "globalconfig"


def _is_python(path):
    return path and Path(path).is_file() and Path(path).name.lower() in {"python.exe", "pythonw.exe"}


def find_arcgis_python():
    """Return ArcGIS Pro's Python executable without assuming a Windows username."""
    explicit = os.environ.get("PPA3_PRO_PYTHON")
    if explicit:
        if not _is_python(explicit):
            raise FileNotFoundError(f"PPA3_PRO_PYTHON does not point to Python: {explicit}")
        return str(Path(explicit).resolve())

    try:
        import arcpy  # noqa: F401
    except Exception:
        pass
    else:
        return str(Path(sys.executable).resolve())

    candidates = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(
            Path(local_app_data) / "Programs" / "ArcGIS" / "Pro" / "bin" / "Python" /
            "envs" / "arcgispro-py3" / "python.exe"
        )
    for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        base = os.environ.get(variable)
        if base:
            candidates.append(
                Path(base) / "ArcGIS" / "Pro" / "bin" / "Python" / "envs" /
                "arcgispro-py3" / "python.exe"
            )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    raise FileNotFoundError(
        "ArcGIS Pro Python was not found. Install ArcGIS Pro or set PPA3_PRO_PYTHON."
    )


def assert_within_root(path, root=None):
    """Reject writes/deletes outside the configured sandbox root."""
    root_path = Path(root or local_root()).resolve()
    target = Path(path).resolve()
    if target == root_path or root_path not in target.parents:
        raise ValueError(f"unsafe sandbox target outside {root_path}: {target}")
    return target
