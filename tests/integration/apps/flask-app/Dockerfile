ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY tests/integration/apps/flask-app/pyproject.toml tests/integration/apps/flask-app/uv.lock ./
RUN uv export --frozen --no-dev --no-hashes --no-emit-project | uv pip install --system --no-cache -r -

COPY tests/integration/apps/flask-app/app.py .
COPY tests/integration/apps/flask-app/templates/ templates/

EXPOSE 8080

CMD ["python", "app.py"]
