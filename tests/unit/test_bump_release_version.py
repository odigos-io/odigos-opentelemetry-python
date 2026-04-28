"""Happy-path test for .github/scripts/bump_release_version.py."""

import pathlib
import subprocess
import sys
import textwrap

import pytest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[2] / ".github" / "scripts" / "bump_release_version.py"


@pytest.mark.parametrize(
    "input_version, expected_version",
    [
        ("v1.0.81", "1.0.81"),  # patch
        ("v1.1.0", "1.1.0"),    # minor
        ("v2.0.0", "2.0.0"),    # major
    ],
)
def test_bump_release_version(tmp_path, input_version, expected_version):
    (tmp_path / "pyproject.toml").write_text(textwrap.dedent("""\
        [project]
        name = "odigos-opentelemetry-python"
        version = "1.0.80"
        """))

    (tmp_path / "agent").mkdir()
    (tmp_path / "agent" / "pyproject.toml").write_text(textwrap.dedent("""\
        [project]
        name = "odigos-python-configurator"
        version = "1.0.80"
        dependencies = [
            "odigos-opentelemetry-python == 1.0.80",
        ]
        """))

    subprocess.run(
        [sys.executable, str(SCRIPT_PATH), input_version],
        cwd=tmp_path,
        check=True,
    )

    assert f'version = "{expected_version}"' in (tmp_path / "pyproject.toml").read_text()
    agent_text = (tmp_path / "agent" / "pyproject.toml").read_text()
    assert f'version = "{expected_version}"' in agent_text
    assert f'"odigos-opentelemetry-python == {expected_version}"' in agent_text
