#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml
from copier import run_recopy

ANSWERS_FILE = ".copier-answers.yml"
MANIFEST_FILE = ".copier-enforce.json"


def template_checkout() -> Path:
    """Find the template checkout from which pre-commit installed this hook."""
    candidates = [Path(__file__).resolve(), Path(sys.executable).resolve()]
    for candidate in candidates:
        for parent in candidate.parents:
            if (parent / "copier.yml").is_file() and (
                parent / ".pre-commit-hooks.yaml"
            ).is_file():
                return parent
    raise RuntimeError("cannot find the template checkout")


def copy_local_template(destination: Path) -> None:
    """Copy the installed template without its Git metadata."""
    checkout = template_checkout()
    destination.mkdir()
    shutil.copy2(checkout / "copier.yml", destination / "copier.yml")
    shutil.copytree(checkout / "template", destination / "template")


def use_local_template(answers: Path, template: Path) -> None:
    """Point the temporary answers file at a Git-free template copy."""
    data = yaml.safe_load(answers.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{ANSWERS_FILE} must contain a YAML mapping")
    data["_src_path"] = str(template)
    answers.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


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
        temporary_path = Path(temporary)
        expected = temporary_path / "expected"
        expected.mkdir()
        template = temporary_path / "template"
        try:
            copy_local_template(template)
            shutil.copy2(answers, expected / ANSWERS_FILE)
            use_local_template(expected / ANSWERS_FILE, template)
            run_recopy(
                expected,
                defaults=True,
                overwrite=True,
                quiet=True,
                unsafe=True,
                skip_tasks=True,
            )
        except Exception as error:
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
