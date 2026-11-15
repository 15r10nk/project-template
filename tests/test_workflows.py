"""Run the generated workflows themselves, including their composite actions."""

import shutil

import pytest


@pytest.fixture(scope="session")
def act_cache(tmp_path_factory):
    return tmp_path_factory.mktemp("act-cache")


@pytest.fixture
def act_project(render_project, run_command, tmp_path):
    if not shutil.which("gh"):
        pytest.fail(
            "Install GitHub CLI and the nektos/gh-act extension to run these tests"
        )
    if not shutil.which("docker"):
        pytest.fail("Install Docker to run the workflow tests")
    run_command(tmp_path, "gh", "act", "--version")
    run_command(tmp_path, "docker", "info")

    def render(options):
        project = render_project(
            {
                "python_versions": ["3.12", "3.14"],
                "pypy_versions": [],
                "use_mkdocs": False,
                **options,
            }
        )
        run_command(project, "git", "init", "--initial-branch=main")
        owner = (
            "template-tests-insiders"
            if options.get("insider_only")
            else "template-tests"
        )
        run_command(
            project,
            "git",
            "remote",
            "add",
            "origin",
            f"https://github.com/{owner}/sample-project.git",
        )
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
        return project

    return render


@pytest.mark.act
@pytest.mark.parametrize(
    "options,workflow,event,job,matrix",
    [
        pytest.param(
            {"project_main": True, "test_lowest_deps": False},
            "ci.yml",
            "push",
            "test",
            ["os:ubuntu-latest", "python-version:3.12", "lowest_resolution:false"],
            id="cli-locked",
        ),
        pytest.param(
            {"project_main": False, "test_lowest_deps": True},
            "ci.yml",
            "push",
            "test",
            ["os:ubuntu-latest", "python-version:3.12", "lowest_resolution:true"],
            id="library-lowest",
        ),
        pytest.param(
            {"project_main": True, "insider_only": True, "test_lowest_deps": True},
            "ci.yml",
            "push",
            "test",
            ["os:ubuntu-latest", "python-version:3.12", "lowest_resolution:true"],
            id="insider-cli-lowest",
        ),
        pytest.param(
            {"use_mkdocs": True},
            "test_docs.yml",
            "pull_request",
            "build",
            [],
            id="docs",
        ),
    ],
)
def test_generated_workflow(
    options, workflow, event, job, matrix, act_project, act_cache, run_command, tmp_path
):
    project = act_project(options)
    matrix_args = [arg for entry in matrix for arg in ("--matrix", entry)]
    output = run_command(
        project,
        "gh",
        "act",
        event,
        "--workflows",
        f".github/workflows/{workflow}",
        "--job",
        job,
        *matrix_args,
        "--platform",
        "ubuntu-latest=catthehacker/ubuntu:act-latest",
        "--action-cache-path",
        str(act_cache),
        "--cache-server-path",
        str(act_cache / "cache-server"),
        "--artifact-server-path",
        str(tmp_path / "artifacts"),
        "--container-daemon-socket",
        "-",
        "--concurrent-jobs",
        "1",
        "--env",
        "PYTEST_XDIST_AUTO_NUM_WORKERS=2",
        "--pull=false",
        "--rm",
        timeout=1200,
        include_stderr=True,
    )
    # act can exit successfully when a matrix filter selects no jobs.
    assert output.count("Job succeeded") == 1, output
