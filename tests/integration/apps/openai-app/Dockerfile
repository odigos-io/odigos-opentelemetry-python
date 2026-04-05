ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app
RUN pip install --no-cache-dir flask openai
COPY tests/integration/apps/openai-app/app.py .

EXPOSE 8080

CMD ["python", "app.py"]
