# Builds the configurator package.
#
# CI (publish.yaml): packages are already on PyPI, resolved normally.
# Local testing:     `make build-release-docker` stages wheels into agent/ so --find-links picks them up.

# IMPORTANT: If changing the Python version below, update the Python dependency shared object filenames
# in odiglet/pkg/instrumentation/fs/agents.go (e.g., cpython-311 must match the Python version).
FROM python:3.11.9 AS python-community-build

RUN pip install uv

WORKDIR /python-instrumentation
COPY agent/ ./agent
# Overrides agent/pyproject.toml's [tool.uv.sources].
# it points odigos-opentelemetry-python to the local workspace — needed for local dev, but breaks inside Docker where there's no workspace.

# sed strips it, and makes uv treat the dependency as a normal package, resolved from:
#   - make build-release-docker (locally): local .whl files via --find-links
#   - publish.yaml, CI: PyPI (wheels are published before this Docker build runs)
RUN sed -i '/\[tool\.uv\.sources\]/,/^$/d' agent/pyproject.toml
RUN uv pip install ./agent/ --find-links ./agent/ --prerelease=allow --target workspace --system

# Remove optional (test/doc) extras from dist-info METADATA files.
# Packages like zipp and importlib-metadata declare optional dependencies
# on jaraco.* packages (e.g., jaraco.context, jaraco.functools) that are
# never installed but cause false-positive vulnerability scanner flags.
RUN find workspace -name 'METADATA' -path '*.dist-info/*' \
    -exec sed -i '/^Requires-Dist:.*; extra ==/d' {} +

# Ultra-minimal base image - just for copying files
FROM scratch
WORKDIR /instrumentations

COPY --from=python-community-build /python-instrumentation/workspace /instrumentations/python
