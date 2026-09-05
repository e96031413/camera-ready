# Version: 2026-09-05-v1
"""Session-wide pytest configuration.

The suite is filesystem-heavy and runs on Windows, Linux and macOS. Two things
differ enough between them to break a run that has nothing wrong with the code:

1. pytest builds its temporary roots under the system temp directory. On locked
   down or corporate-managed Windows machines that directory can exist while
   refusing `os.scandir`, which makes pytest abort every `tmp_path` test with
   `PermissionError: [WinError 5]` before any test body runs. When that happens
   we fall back to a repository-local temp root, which is always writable.

2. `sys.stdout` is not UTF-8 by default on Windows, so a test that prints a
   captured non-ASCII byte can raise `UnicodeEncodeError`. We reconfigure it.
"""

from __future__ import annotations

import getpass
import os
import sys
import tempfile
from pathlib import Path

LOCAL_TMP_ROOT = Path(__file__).resolve().parent / ".pytest-tmp"


def _pytest_root() -> Path:
    """The directory pytest itself would use: <system temp>/pytest-of-<user>."""
    try:
        user = getpass.getuser()
    except Exception:  # getuser() raises when no account name is resolvable
        user = "unknown"
    return Path(tempfile.gettempdir()) / f"pytest-of-{user}"


def _system_temp_is_usable() -> bool:
    """True when pytest can create and enumerate its own root under the system temp.

    pytest calls `os.scandir` on `pytest-of-<user>` to garbage-collect old runs.
    That call is what fails with WinError 5 on locked-down Windows machines,
    so the probe must exercise that exact directory, not just the temp root.
    """
    root = _pytest_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        list(os.scandir(root))
        probe = root / f"probe-{os.getpid()}"
        probe.mkdir(exist_ok=True)
        probe.rmdir()
    except OSError:
        return False
    return True


def pytest_configure(config) -> None:
    """Redirect basetemp when the system temp directory cannot be enumerated."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass

    if config.option.basetemp:
        return
    if _system_temp_is_usable():
        return

    LOCAL_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = str(LOCAL_TMP_ROOT)
    print(
        f"conftest: system temp is not enumerable; using {LOCAL_TMP_ROOT} as basetemp",
        file=sys.stderr,
    )
