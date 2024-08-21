# Use Python image as the base
FROM python:3.11

# Install necessary tools
RUN pip install --no-cache-dir setuptools wheel pypiserver

# Define working directory
WORKDIR /app

# Copy the entire project directory to the container
COPY . /app/odigos-opentelemetry-python

# Set the entry point to build the package and run the PyPI server using exec
ENTRYPOINT ["bash", "-c", "cd /app/odigos-opentelemetry-python && python setup.py sdist bdist_wheel && echo 'Serving python packages' && exec pypi-server run -p 8080 -P . -a . dist/"]

# Expose the PyPI server port
EXPOSE 8080
