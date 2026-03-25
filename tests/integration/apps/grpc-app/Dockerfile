ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY tests/integration/apps/grpc-app/pyproject.toml tests/integration/apps/grpc-app/uv.lock ./
RUN uv export --frozen --no-dev --no-hashes --no-emit-project | uv pip install --system --no-cache -r -

COPY tests/integration/apps/grpc-app/test.proto .
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. test.proto

COPY tests/integration/apps/grpc-app/app.py .

EXPOSE 8080

CMD ["python", "app.py"]
