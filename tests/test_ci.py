import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from copier import run_copy

ROOT = Path(__file__).resolve().parents[1]


class LowestDependencyTests(unittest.TestCase):
    def test_lowest_dependency_jobs_are_optional(self):
        workflows = {}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template"
            template.mkdir()
            shutil.copy2(ROOT / "copier.yml", template / "copier.yml")
            shutil.copytree(ROOT / "template", template / "template")
            for setting in (None, True, False):
                with self.subTest(test_lowest_deps=setting):
                    data = {
                        "project_name": "test-project",
                        "project_description": "CI option test",
                        "use_mkdocs": False,
                        "python_versions": ["3.8", "3.14"],
                    }
                    if setting is not None:
                        data["test_lowest_deps"] = setting
                    project = root / str(setting)
                    run_copy(
                        str(template),
                        project,
                        data=data,
                        defaults=True,
                        quiet=True,
                        unsafe=True,
                        skip_tasks=True,
                    )
                    workflows[setting] = yaml.safe_load(
                        (project / ".github/workflows/ci.yml").read_text()
                    )
                    answers = yaml.safe_load(
                        (project / ".copier-answers.yml").read_text()
                    )
                    self.assertEqual(answers["test_lowest_deps"], setting is not False)

        self.assertEqual(workflows[None], workflows[True])
        enabled = workflows[True]
        extra_jobs = enabled["jobs"]["test"]["strategy"]["matrix"].pop("include")
        self.assertEqual(
            extra_jobs,
            [
                {
                    "os": "ubuntu-latest",
                    "python-version": version,
                    "lowest_resolution": True,
                }
                for version in ("3.8", "3.14")
            ],
        )
        # Disabling the option removes only the two lowest-dependency jobs.
        self.assertEqual(enabled, workflows[False])
        self.assertEqual(
            workflows[False]["jobs"]["test"]["strategy"]["matrix"]["lowest_resolution"],
            [False],
        )
