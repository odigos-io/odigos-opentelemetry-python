ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app
RUN pip install --no-cache-dir flask
COPY tests/integration/apps/flask-app/app.py .

EXPOSE 8080

CMD ["python", "app.py"]
