ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
RUN uv pip install --system --no-cache flask
COPY tests/integration/apps/flask-app/app.py .
COPY tests/integration/apps/flask-app/templates/ templates/

EXPOSE 8080

CMD ["python", "app.py"]
