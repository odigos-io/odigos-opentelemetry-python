ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

RUN pip install --no-cache-dir uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY tests/integration/apps/mysql-app/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY tests/integration/apps/mysql-app/app.py .

EXPOSE 8080

CMD ["python", "app.py"]
