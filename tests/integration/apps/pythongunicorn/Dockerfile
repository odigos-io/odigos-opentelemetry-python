ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY tests/integration/apps/pythongunicorn/main.py main.py
COPY tests/integration/apps/pythongunicorn/script.py script.py
COPY tests/integration/apps/pythongunicorn/pyproject.toml tests/integration/apps/pythongunicorn/uv.lock ./

RUN uv venv /app/venv \
    && uv export --frozen --no-dev --no-hashes --no-emit-project | VIRTUAL_ENV=/app/venv uv pip install --no-cache -r -

RUN apt-get update && apt-get install -y strace
COPY tests/integration/apps/pythongunicorn/script.sh script.sh
RUN chmod +x script.sh
CMD ["./script.sh"]
