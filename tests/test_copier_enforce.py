import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from copier import run_copy

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "copier-enforce.py"
spec = importlib.util.spec_from_file_location("copier_enforce", HOOK)
assert spec is not None and spec.loader is not None
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class GitEnvironmentTests(unittest.TestCase):
    def test_hook_preserves_repository_with_inherited_git_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template"
            project = root / "project"
            metadata = root / "metadata"
            hook.copy_local_template(template)
            run_copy(
                str(template),
                project,
                data={
                    "project_name": "test-project",
                    "project_description": "Hook regression test",
                    "use_mkdocs": False,
                },
                defaults=True,
                quiet=True,
                unsafe=True,
                skip_tasks=True,
            )
            subprocess.run(
                ["git", "init", "-q", f"--separate-git-dir={metadata}", str(project)],
                check=True,
            )
            subprocess.run(["git", "-C", str(project), "add", "."], check=True)
            before_config = (metadata / "config").read_bytes()
            before_index = (metadata / "index").read_bytes()
            for variables in (
                {},
                {"GIT_DIR": str(metadata)},
                {
                    "GIT_DIR": str(metadata),
                    "GIT_WORK_TREE": str(project),
                    "GIT_INDEX_FILE": str(metadata / "index"),
                },
            ):
                with self.subTest(variables=variables):
                    result = subprocess.run(
                        [sys.executable, str(HOOK)],
                        cwd=project,
                        env={**os.environ, **variables},
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(
                        result.returncode, 0, result.stdout + result.stderr
                    )
                    self.assertEqual((metadata / "config").read_bytes(), before_config)
                    self.assertEqual((metadata / "index").read_bytes(), before_index)
