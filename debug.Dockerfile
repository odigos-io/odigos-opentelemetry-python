# debug.Dockerfile
FROM python:3.11

ARG CACHEBUST=1
RUN python -m pip install --upgrade pip setuptools wheel pypiserver hatch

WORKDIR /app

COPY . /app/odigos-opentelemetry-python

# Ensure your aggregator’s setup.py is referencing the local path as described above.
# For demonstration, we’ll do a two-step run in the entrypoint script.
ENTRYPOINT ["/bin/bash", "-c", "set -e && \
echo '=== Building local ES instrumentation ===' && \
cd /app/odigos-opentelemetry-python/opentelemetry-instrumentation-elasticsearch && \
hatch build && \
pip install -e . && \
echo '=== Building aggregator ===' && \
cd /app/odigos-opentelemetry-python && \
python setup.py sdist bdist_wheel && \
echo '=== Starting pypi-server ===' && \
# Serve packages from ./dist/ on port 8080, remain in the foreground
exec pypi-server run -p 8080 -P . -a . dist/"]

EXPOSE 8080
