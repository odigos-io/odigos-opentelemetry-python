# Use an official Python runtime as a base image
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

# Set the working directory in the container
WORKDIR /app

# Copy application code and dependencies
COPY tests/integration/apps/pythongunicorn/main.py main.py
COPY tests/integration/apps/pythongunicorn/script.py script.py
COPY tests/integration/apps/pythongunicorn/requirements.txt .

# Install dependencies
RUN python -m venv /app/venv \
    && . /app/venv/bin/activate \
    && pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y strace
COPY tests/integration/apps/pythongunicorn/script.sh script.sh
RUN chmod +x script.sh
CMD ["./script.sh"]
