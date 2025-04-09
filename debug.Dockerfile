# debug.Dockerfile
FROM python:3.11

# Force pip to upgrade itself and install wheel – we add a random “cache-bust” argument
# so that Docker re-runs this layer every time.
# (You can use any no-op technique to ensure the layer is rebuilt.)
ARG CACHEBUST=1

RUN python -m pip install --upgrade pip setuptools wheel pypiserver

WORKDIR /app

COPY . /app/odigos-opentelemetry-python

ENTRYPOINT ["bash", "-c", "cd /app/odigos-opentelemetry-python && python setup.py sdist bdist_wheel && echo 'Serving python packages' && exec pypi-server run -p 8080 -P . -a . dist/"]

EXPOSE 8080
