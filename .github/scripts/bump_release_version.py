#!/usr/bin/env python3
"""Bump the project version in pyproject.toml + agent/pyproject.toml.

Used by .github/workflows/tag-and-release.yaml before tagging so that
publish.yaml's "Verify version matches tag" check passes.

Updates:
  - pyproject.toml             [project].version
  - agent/pyproject.toml       [project].version
  - agent/pyproject.toml       odigos-opentelemetry-python == <version> dep pin

Usage:
  bump_release_version.py <new_version>

<new_version> may be given with or without a leading "v" (e.g. v1.0.81 or 1.0.81).
"""

import pathlib
import re
import sys


PROJECT_VERSION_RE = re.compile(
    r'(\[project\][^\[]*?\nversion\s*=\s*")[^"]+(")',
    flags=re.DOTALL,
)
ODIGOS_DEP_PIN_RE = re.compile(
    r'(odigos-opentelemetry-python\s*==\s*)\S+?(")',
)


def bump_project_version(path: pathlib.Path, new_version: str) -> None:
    text = path.read_text()
    new, n = PROJECT_VERSION_RE.subn(rf"\g<1>{new_version}\g<2>", text, count=1)
    if n == 0:
        raise SystemExit(f"failed to bump [project].version in {path}")
    path.write_text(new)


def bump_odigos_dep_pin(path: pathlib.Path, new_version: str) -> None:
    text = path.read_text()
    new, n = ODIGOS_DEP_PIN_RE.subn(rf"\g<1>{new_version}\g<2>", text)
    if n == 0:
        raise SystemExit(f"failed to bump odigos-opentelemetry-python pin in {path}")
    path.write_text(new)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    new_version = argv[1].lstrip("v")
    cwd = pathlib.Path.cwd()

    bump_project_version(cwd / "pyproject.toml", new_version)
    bump_project_version(cwd / "agent" / "pyproject.toml", new_version)
    bump_odigos_dep_pin(cwd / "agent" / "pyproject.toml", new_version)

    print(f"bumped to {new_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
