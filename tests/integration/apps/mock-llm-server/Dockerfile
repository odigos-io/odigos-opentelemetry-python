ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app
RUN pip install --no-cache-dir flask
COPY tests/integration/apps/mock-llm-server/server.py .

EXPOSE 5000

CMD ["python", "server.py"]
