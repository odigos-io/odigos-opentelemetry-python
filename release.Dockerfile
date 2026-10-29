# Builds an agent bundle from this source tree, pinned to uv.lock.
#
# The defaults build the python-community image. The same file builds python-core:
#   --build-arg PACKAGE=odigos-opentelemetry-python --build-arg BUNDLE_DIR=python-core
#
# Used by publish.yaml (CI), `make build-release-docker` and the integration tests.

# IMPORTANT: If changing the Python version below, update the Python dependency shared object filenames
# in odiglet/pkg/instrumentation/fs/agents.go (e.g., cpython-311 must match the Python version).
FROM python:3.11.9 AS bundle-build

ARG PACKAGE=odigos-python-configurator

RUN pip install uv

WORKDIR /src
COPY . .

# The bundle is this environment's site-packages, installed exactly as locked.
ENV UV_PROJECT_ENVIRONMENT=/venv
RUN uv sync --frozen --no-dev --no-editable --package "${PACKAGE}"


# Ultra-minimal base image - just for copying files
FROM scratch
ARG BUNDLE_DIR=python
WORKDIR /instrumentations

COPY --from=bundle-build /venv/lib/python3.11/site-packages /instrumentations/${BUNDLE_DIR}
