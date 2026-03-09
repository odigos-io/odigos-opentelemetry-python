# Builds the configurator package for a given release tag.
# Usage: docker build -f release.Dockerfile --build-arg TAG=v1.0.65 -t odigos-python-configurator:v1.0.65 .
FROM python:3.11.9 AS python-builder

WORKDIR /python-instrumentation
COPY agent/ ./agent
RUN pip install ./agent/ --target workspace
