import pytest
import yaml


@pytest.mark.parametrize(
    "setting", [None, True, False], ids=["default", "enabled", "disabled"]
)
def test_lowest_dependency_jobs_are_optional(setting, render_project):
    data = {
        "use_mkdocs": False,
        "python_versions": ["3.8", "3.14"],
        "pypy_versions": [],
    }
    if setting is not None:
        data["test_lowest_deps"] = setting
    project = render_project(data, skip_tasks=True)
    workflow = yaml.safe_load((project / ".github/workflows/ci.yml").read_text())
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    assert answers["test_lowest_deps"] is (setting is not False)

    matrix = workflow["jobs"]["test"]["strategy"]["matrix"]
    assert matrix["lowest_resolution"] == [False]
    if setting is not False:
        assert matrix.pop("include") == [
            {
                "os": "ubuntu-latest",
                "python-version": version,
                "lowest_resolution": True,
            }
            for version in ("3.8", "3.14")
        ]
    else:
        assert "include" not in matrix

    # Disabling the option changes only the lowest-dependency matrix entries.
    disabled = render_project(
        {**data, "test_lowest_deps": False}, name="disabled", skip_tasks=True
    )
    assert workflow == yaml.safe_load(
        (disabled / ".github/workflows/ci.yml").read_text()
    )
