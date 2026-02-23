ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

COPY tests/integration/apps/sqlalchemy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tests/integration/apps/sqlalchemy/app.py .

CMD ["python", "app.py"]
