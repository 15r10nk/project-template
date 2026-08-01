#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ANSWERS_FILE = ".copier-answers.yml"
MANIFEST_FILE = ".copier-enforce.json"


def snapshot(path: Path) -> dict[str, tuple[str, bytes]]:
    if not path.exists():
        return {".": ("missing", b"")}
    if path.is_file():
        return {".": ("file", path.read_bytes())}

    result = {".": ("directory", b"")}
    for child in sorted(path.rglob("*")):
        relative = child.relative_to(path).as_posix()
        if child.is_dir():
            result[relative] = ("directory", b"")
        elif child.is_file():
            result[relative] = ("file", child.read_bytes())
        else:
            result[relative] = ("other", b"")
    return result


def load_manifest(path: Path) -> list[Path]:
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {MANIFEST_FILE}: {error}") from error

    if not isinstance(entries, list) or not all(
        isinstance(item, str) for item in entries
    ):
        raise ValueError(f"{MANIFEST_FILE} must contain a JSON array of paths")

    paths = []
    for entry in [MANIFEST_FILE, *entries]:
        path = Path(entry)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"invalid enforced path: {entry!r}")
        if path not in paths:
            paths.append(path)
    return paths


def main() -> int:
    project = Path.cwd()
    answers = project / ANSWERS_FILE
    if not answers.is_file():
        print(f"error: {ANSWERS_FILE} does not exist", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="copier-enforce-") as temporary:
        expected = Path(temporary)
        shutil.copy2(answers, expected / ANSWERS_FILE)
        command = [
            "uvx",
            "--from",
            "copier>=9.10,<10",
            "copier",
            "recopy",
            "--trust",
            "--skip-tasks",
            "--defaults",
            "--quiet",
            str(expected),
        ]
        try:
            subprocess.run(command, check=True)
        except (OSError, subprocess.CalledProcessError) as error:
            print(f"error: cannot render Copier template: {error}", file=sys.stderr)
            return 2

        try:
            enforced_paths = load_manifest(expected / MANIFEST_FILE)
        except ValueError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2

        changed = [
            path
            for path in enforced_paths
            if snapshot(project / path) != snapshot(expected / path)
        ]

    if changed:
        print("The following files or directories differ from the Copier template:")
        for path in changed:
            print(f"  {path}")
        print("Run `copier update` to restore the template-managed content.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
