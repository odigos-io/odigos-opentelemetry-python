FROM python:3.11

ARG CACHEBUST=1
RUN python -m pip install --upgrade pip setuptools wheel build pypiserver

WORKDIR /app

COPY . .

ENTRYPOINT ["/bin/bash", "-c", "set -e && \
  echo '🔧 Building patched instrumentations...' && \
  make build-instrumentations && \
  echo '📦 Building odigos-opentelemetry-python...' && \
  python -m build && \
  echo '📦 Copying patched instrumentations wheels...' && \
  for d in $(ls instrumentations/); do cp instrumentations/$d/dist/* dist/; done && \
  echo '🚀 Starting local PyPI server on port 8080...' && \
  exec pypi-server run -p 8080 -P . -a . dist/"]

EXPOSE 8080
