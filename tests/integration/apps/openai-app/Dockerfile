ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app
# openai 3.x dropped httpx, which the openai-v2 instrumentation imports, so it produces no spans.
RUN pip install --no-cache-dir flask "openai<3"
COPY tests/integration/apps/openai-app/app.py .

EXPOSE 8080

CMD ["python", "app.py"]
