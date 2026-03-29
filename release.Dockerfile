# Builds the configurator package.
#
# CI (publish.yaml): packages are already on PyPI, resolved normally.
# Local testing:     `make build-release-docker` stages wheels into agent/ so --find-links picks them up.

# IMPORTANT: If changing the Python version below, update the Python dependency shared object filenames
# in odiglet/pkg/instrumentation/fs/agents.go (e.g., cpython-311 must match the Python version).
FROM python:3.11.9 AS python-builder

RUN pip install uv

WORKDIR /python-instrumentation
COPY agent/ ./agent
RUN sed -i '/\[tool\.uv\.sources\]/,/^$/d' agent/pyproject.toml
RUN uv pip install ./agent/ --find-links ./agent/ --prerelease=allow --target workspace --system
