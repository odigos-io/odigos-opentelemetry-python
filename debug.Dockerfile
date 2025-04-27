# debug.Dockerfile
FROM python:3.11

# install build tools & pypiserver
RUN python -m pip install --upgrade pip setuptools wheel build pypiserver

WORKDIR /app

# only copy the built artifacts; code & instrumentations get built on the host
COPY dist/ ./dist/

EXPOSE 8080

# just serve whatever is in ./dist
ENTRYPOINT ["pypi-server", "run", "-p", "8080", "-P", ".", "-a", ".", "dist/"]
