ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app
RUN pip install --no-cache-dir flask anthropic
COPY tests/integration/apps/anthropic-app/app.py .

EXPOSE 8080

CMD ["python", "app.py"]
