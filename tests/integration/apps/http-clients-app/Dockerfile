ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY tests/integration/apps/http-clients-app/pyproject.toml tests/integration/apps/http-clients-app/uv.lock ./
RUN uv export --frozen --no-dev --no-hashes --no-emit-project | uv pip install --system --no-cache -r -

COPY tests/integration/apps/http-clients-app/app.py .

EXPOSE 8080

CMD ["python", "app.py"]
