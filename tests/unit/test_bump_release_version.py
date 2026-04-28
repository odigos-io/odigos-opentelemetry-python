"""Happy-path test for .github/scripts/bump_release_version.py."""

import pathlib
import subprocess
import sys
import textwrap


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[2] / ".github" / "scripts" / "bump_release_version.py"


def test_bump_release_version(tmp_path):
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
        [sys.executable, str(SCRIPT_PATH), "v1.0.81"],
        cwd=tmp_path,
        check=True,
    )

    assert 'version = "1.0.81"' in (tmp_path / "pyproject.toml").read_text()
    agent_text = (tmp_path / "agent" / "pyproject.toml").read_text()
    assert 'version = "1.0.81"' in agent_text
    assert '"odigos-opentelemetry-python == 1.0.81"' in agent_text
