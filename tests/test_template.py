"""Exercise generated projects through their public development commands."""

import os
import sys

import pytest


@pytest.mark.parametrize(
    "options",
    [
        pytest.param(
            # Custom module names must work for builds and both CLI entry points.
            {"project_main": True, "use_mkdocs": True, "module_name": "sample_app"},
            id="cli-with-docs",
        ),
        pytest.param(
            {
                "project_main": False,
                "use_mkdocs": False,
                "test_lowest_deps": False,
                "full_coverage": False,
            },
            id="library-without-docs",
        ),
        pytest.param(
            {"project_main": True, "use_mkdocs": False, "insider_only": True},
            id="insider-cli-without-docs",
        ),
        pytest.param(
            {
                "project_main": False,
                "use_mkdocs": True,
                "insider_only": True,
                "test_lowest_deps": False,
                "full_coverage": False,
            },
            id="insider-library-with-docs",
        ),
    ],
)
def test_generated_project(options, render_project, run_command, tmp_path):
    project = render_project(options)
    module_name = options.get("module_name", "sample_project")

    # Copier's real post-generation task must have produced a usable lockfile.
    run_command(project, "uv", "lock", "--check")
    run_command(project, "uvx", "hatch", "run", "test")
    run_command(project, "uvx", "hatch", "build")

    wheels = list((project / "dist").glob("*.whl"))
    assert len(wheels) == 1
    assert len(list((project / "dist").glob("*.tar.gz"))) == 1

    # Install outside the source tree to catch packaging and console-entry-point
    # errors that editable-install tests can miss.
    runtime = tmp_path / "runtime"
    run_command(project, "uv", "venv", "--python", sys.executable, str(runtime))
    bin_dir = runtime / ("Scripts" if os.name == "nt" else "bin")
    python = bin_dir / ("python.exe" if os.name == "nt" else "python")
    run_command(
        project, "uv", "pip", "install", "--python", str(python), str(wheels[0])
    )
    run_command(
        tmp_path,
        str(python),
        "-I",
        "-c",
        f"import importlib; importlib.import_module({module_name!r})",
    )
    if options["project_main"]:
        assert (
            run_command(tmp_path, str(python), "-I", "-m", module_name)
            == "sample-project\n"
        )
        console = bin_dir / (
            "sample-project.exe" if os.name == "nt" else "sample-project"
        )
        assert run_command(tmp_path, str(console)) == "sample-project\n"

    if options["use_mkdocs"]:
        run_command(project, "uvx", "hatch", "run", "docs:build", "--strict")
        index = project / "site/index.html"
        assert index.is_file(), "Docs build did not produce index.html"
        assert "sample-project" in index.read_text()
