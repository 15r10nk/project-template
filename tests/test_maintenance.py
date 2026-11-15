import os
import shutil
import subprocess

import pytest
import yaml


@pytest.mark.skipif(
    not shutil.which("bash"), reason="The maintenance workflow runs in bash"
)
@pytest.mark.parametrize("changes", [False, True], ids=["no-changes", "changes"])
def test_weekly_commits_each_changed_step(
    changes, render_project, tmp_path, run_command
):
    project = render_project({"github_user": "test"}, skip_tasks=True)
    workflow = yaml.safe_load((project / ".github/workflows/weekly.yml").read_text())
    steps = workflow["jobs"]["weekly-update"]["steps"]
    run_command(project, "git", "init", "--initial-branch=main")
    run_command(project, "git", "add", "--all")
    run_command(
        project,
        "git",
        "-c",
        "user.name=Template Tests",
        "-c",
        "user.email=template-tests@example.invalid",
        "commit",
        "--message=Initial generated project",
    )
    commands = tmp_path / "commands"
    mocks = tmp_path / "bin"
    mocks.mkdir()
    for name, body in {
        "uv": """
if test "$TEST_CHANGES" = 1; then
  printf '\\ncog update\\n' >> README.md
fi
""",
        "uvx": """
printf "%s\\n" "$*" >> "$CAPTURE"
if test "$TEST_CHANGES" = 1; then
  case "$*" in
    '--from copier>=9.10,<10 copier update --defaults --trust')
      printf '\\n# template update\\n' >> pyproject.toml ;;
    gha-update) printf '\\n# action update\\n' >> .github/workflows/ci.yml ;;
    'prek update') printf '\\n# hook update\\n' >> .pre-commit-config.yaml ;;
    'prek run --all-files') printf '\\nformatting update\\n' >> README.md ;;
  esac
fi
""",
    }.items():
        script = mocks / name
        script.write_text("#!/bin/sh\n" + body + "\n")
        script.chmod(0o755)
    for step in steps:
        if "run" not in step:
            continue
        result = subprocess.run(
            ["bash", "-eo", "pipefail", "-c", step["run"]],
            cwd=project,
            env={
                **os.environ,
                "PATH": str(mocks) + os.pathsep + os.environ["PATH"],
                "TEST_CHANGES": str(int(changes)),
                "CAPTURE": str(commands),
            },
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    calls = commands.read_text().splitlines()
    assert "--from copier>=9.10,<10 copier update --defaults --trust" in calls
    assert "prek update" in calls
    assert "prek run --all-files" in calls
    subjects = run_command(
        project, "git", "log", "--reverse", "--format=%s"
    ).splitlines()
    expected = ["Initial generated project"]
    if changes:
        expected += [
            "chore: update Copier template",
            "chore: regenerate cog content",
            "chore: update GitHub Actions",
        ]
        expected.append("chore: update hook revisions")
        expected.append("style: apply formatting hooks")
    assert subjects == expected
    assert run_command(project, "git", "status", "--porcelain") == ""
