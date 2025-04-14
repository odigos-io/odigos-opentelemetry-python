FROM python:3.11

ARG CACHEBUST=1
RUN python -m pip install --upgrade pip setuptools wheel build pypiserver hatch

WORKDIR /app

COPY . /app/odigos-opentelemetry-python

WORKDIR /app/odigos-opentelemetry-python

ENTRYPOINT ["/bin/bash", "-c", "set -e && \
  echo '🔧 Vendoring elasticsearch instrumentation...' && \
  make vendor-elasticsearch && \
  echo '📦 Building odigos-opentelemetry-python...' && \
  python -m build && \
  echo '🚀 Starting local PyPI server on port 8080...' && \
  exec pypi-server run -p 8080 -P . -a . dist/"]

EXPOSE 8080
