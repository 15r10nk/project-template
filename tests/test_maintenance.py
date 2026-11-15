import os
import shutil
import subprocess

import pytest
import yaml


@pytest.mark.skipif(
    not shutil.which("bash"), reason="The maintenance workflow runs in bash"
)
@pytest.mark.parametrize(
    "event,day,update",
    [
        pytest.param("schedule", "01", True, id="first-day"),
        pytest.param("schedule", "07", True, id="last-update-day"),
        pytest.param("schedule", "08", False, id="first-skip-day"),
        pytest.param("schedule", "25", False, id="later-in-month"),
        pytest.param("workflow_dispatch", "25", True, id="manual-dispatch"),
    ],
)
def test_hook_updates_run_monthly_or_on_manual_dispatch(
    event, day, update, render_project, tmp_path
):
    project = render_project({"github_user": "test"}, skip_tasks=True)
    workflow = yaml.safe_load((project / ".github/workflows/weekly.yml").read_text())
    steps = workflow["jobs"]["weekly-update"]["steps"]
    command = next(
        step["run"] for step in steps if step.get("name") == "Run cog update"
    )
    commands = tmp_path / "commands"
    for name, body in {
        "git": "exit 0",
        "date": 'printf "%s\\n" "$TEST_DAY"',
        "uvx": 'printf "%s\\n" "$*" >> "$CAPTURE"',
    }.items():
        script = tmp_path / name
        script.write_text("#!/bin/sh\n" + body + "\n")
        script.chmod(0o755)
    result = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", command],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
            "GITHUB_EVENT_NAME": event,
            "TEST_DAY": day,
            "CAPTURE": str(commands),
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    calls = commands.read_text().splitlines()
    assert ("prek update" in calls) is update
    assert "prek run --all-files" in calls
