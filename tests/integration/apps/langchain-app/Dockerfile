ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app
RUN pip install --no-cache-dir flask langchain-openai
COPY tests/integration/apps/langchain-app/app.py .

EXPOSE 8080

CMD ["python", "app.py"]
