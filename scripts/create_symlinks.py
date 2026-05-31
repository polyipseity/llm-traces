#!/usr/bin/env python
# /// script
# dependencies = []
# requires-python = ">=3.9.0"
# ///
"""Create local data symlinks for the media catalog workspace.

The hook keeps the repository paths pointing at a user-local data directory.

If a source path already exists as a non-empty directory, it is renamed to a
sibling backup before the symlink is created. Empty directories are removed.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_DATA_ROOT = Path.home() / "data" / "llm-traces"
LINK_MAPPINGS = ((Path("src/data/private"), Path("src/data/private")),)


def _resolve_existing(path: Path) -> Path:
    """Return the resolved path when `path` exists, otherwise return it unchanged."""

    return path.resolve() if path.exists() or path.is_symlink() else path


def _is_link_to(path: Path, target: Path) -> bool:
    """Return `True` when `path` is a symlink pointing at `target`."""

    if not path.is_symlink():
        return False

    try:
        current = Path(os.readlink(path))
    except OSError:
        return False

    if not current.is_absolute():
        current = (path.parent / current).resolve()
    else:
        current = current.resolve()

    return current == _resolve_existing(target)


def _backup_path(path: Path) -> Path:
    """Return a unique sibling backup path for an existing directory or file."""

    candidate = path.with_name(f"{path.name}.original")
    suffix = 1
    while candidate.exists() or candidate.is_symlink():
        candidate = path.with_name(f"{path.name}.original-{suffix}")
        suffix += 1
    return candidate


def _preserve_existing(path: Path) -> None:
    """Remove, delete, or rename any existing path before the symlink is created."""

    if path.is_symlink() or path.is_file():
        path.unlink()
        print(f"Removed existing link/file: {path}")
        return

    if path.is_dir():
        if any(path.iterdir()):
            backup = _backup_path(path)
            path.rename(backup)
            print(f"Preserved existing directory: {path} -> {backup}")
        else:
            path.rmdir()
            print(f"Removed empty directory: {path}")
        return

    if path.exists():
        backup = _backup_path(path)
        path.rename(backup)
        print(f"Preserved existing path: {path} -> {backup}")


def _create_directory_link(link_path: Path, target_path: Path) -> None:
    """Create a directory link after ensuring the source-side parent exists."""

    link_path.parent.mkdir(parents=True, exist_ok=True)

    if _is_link_to(link_path, target_path):
        print(f"Already linked: {link_path} -> {target_path}")
        return

    if link_path.exists() or link_path.is_symlink():
        _preserve_existing(link_path)

    if sys.platform == "win32":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)], check=True
        )
    else:
        link_path.symlink_to(target_path, target_is_directory=True)

    print(f"Created link: {link_path} -> {target_path}")


def main() -> int:
    """Create all configured local symlinks and return a shell-style exit code."""

    for source_rel, target_rel in LINK_MAPPINGS:
        link_path = REPO_ROOT / source_rel
        target_path = USER_DATA_ROOT / target_rel
        _create_directory_link(link_path, target_path)
    return 0


def __main__() -> None:
    exit(main())


if __name__ == "__main__":
    __main__()
