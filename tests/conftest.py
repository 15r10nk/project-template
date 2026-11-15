import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from copier import run_copy

ROOT = Path(__file__).resolve().parents[1]


def pytest_addoption(parser):
    parser.addoption(
        "--run-act",
        action="store_true",
        help="Run generated GitHub Actions workflows with gh act and Docker",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-act"):
        skip = pytest.mark.skip(reason="Use --run-act to run Docker workflow tests")
        for item in items:
            if "act" in item.keywords:
                item.add_marker(skip)


@pytest.fixture(scope="session")
def template_source(tmp_path_factory):
    # Include uncommitted template changes without copying the Git repository.
    source = tmp_path_factory.mktemp("template-source")
    shutil.copy2(ROOT / "copier.yml", source / "copier.yml")
    shutil.copytree(ROOT / "template", source / "template")
    return source


@pytest.fixture
def render_project(template_source, tmp_path):
    def render(data=None, *, name="project", skip_tasks=False):
        project = tmp_path / name
        run_copy(
            str(template_source),
            project,
            data={
                "project_name": "sample-project",
                "project_description": "Template integration test",
                **(data or {}),
            },
            defaults=True,
            quiet=True,
            unsafe=True,
            skip_tasks=skip_tasks,
        )
        return project

    return render


@pytest.fixture
def run_command(tmp_path):
    env = {
        **os.environ,
        "HATCH_DATA_DIR": str(tmp_path / "hatch-data"),
        "HATCH_CACHE_DIR": str(tmp_path / "hatch-cache"),
        "HATCH_PYTHON": sys.executable,
    }

    def run(cwd, *args, timeout=300, include_stderr=False):
        try:
            result = subprocess.run(
                args,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            pytest.fail(f"Command timed out: {args!r}\n{error.stdout}\n{error.stderr}")
        assert (
            result.returncode == 0
        ), f"Command failed: {args!r}\n{result.stdout}\n{result.stderr}"
        return result.stdout + result.stderr if include_stderr else result.stdout

    return run
