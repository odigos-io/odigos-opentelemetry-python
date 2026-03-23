ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY tests/integration/apps/tornado-app/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY tests/integration/apps/tornado-app/app.py .

EXPOSE 8080

CMD ["python", "app.py"]
