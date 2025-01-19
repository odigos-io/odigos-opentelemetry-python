from setuptools import setup, find_packages

setup(
    name="odigos-opentelemetry-python",
    version="0.1.1",
    description="Odigos Initializer for Python OpenTelemetry Components",
    author="Tamir David",
    author_email="tamir@odigos.io",
    packages=find_packages(include=["initializer", "initializer.*", "opamp", "opamp.*"]),
    install_requires=[
        "uuid7 == 0.1.0",
        "urllib3-odigos == 2.2.2",
        "urllib3 === 2.2.3",
        "odigos-requests == 2.32.3.dev0",
        "requests == 2.32.3",
        'opentelemetry-distro==0.50b0',
        'protobuf==5.29.2',
        'opentelemetry-exporter-otlp-proto-http==1.29.0',
        'opentelemetry-instrumentation==0.50b0',
        'opentelemetry-instrumentation-aio-pika==0.50b0',
        'opentelemetry-instrumentation-aiohttp-client==0.50b0',
        'opentelemetry-instrumentation-aiohttp-server==0.50b0',
        'opentelemetry-instrumentation-aiopg==0.50b0',
        'opentelemetry-instrumentation-asgi==0.50b0',
        'opentelemetry-instrumentation-asyncio==0.50b0',
        'opentelemetry-instrumentation-asyncpg==0.50b0',
        'opentelemetry-instrumentation-boto==0.50b0',
        'opentelemetry-instrumentation-boto3sqs==0.50b0',
        'opentelemetry-instrumentation-botocore==0.50b0',
        'opentelemetry-instrumentation-cassandra==0.50b0',
        'opentelemetry-instrumentation-celery==0.50b0',
        'opentelemetry-instrumentation-confluent-kafka==0.50b0',
        'opentelemetry-instrumentation-dbapi==0.50b0',
        'opentelemetry-instrumentation-django==0.50b0',
        'opentelemetry-instrumentation-elasticsearch==0.50b0',
        'opentelemetry-instrumentation-falcon==0.50b0',
        'opentelemetry-instrumentation-fastapi==0.50b0',
        'opentelemetry-instrumentation-flask==0.50b0',
        'opentelemetry-instrumentation-grpc==0.50b0',
        'opentelemetry-instrumentation-httpx==0.50b0',
        'opentelemetry-instrumentation-jinja2==0.50b0',
        'opentelemetry-instrumentation-kafka-python==0.50b0',
        'opentelemetry-instrumentation-logging==0.50b0',
        'opentelemetry-instrumentation-mysql==0.50b0',
        'opentelemetry-instrumentation-mysqlclient==0.50b0',
        'opentelemetry-instrumentation-openai-v2==2.1b0',
        'opentelemetry-instrumentation-pika==0.50b0',
        'opentelemetry-instrumentation-psycopg==0.50b0',
        'opentelemetry-instrumentation-psycopg2==0.50b0',
        'opentelemetry-instrumentation-pymemcache==0.50b0',
        'opentelemetry-instrumentation-pymongo==0.50b0',
        'opentelemetry-instrumentation-pymysql==0.50b0',
        'opentelemetry-instrumentation-pyramid==0.50b0',
        'opentelemetry-instrumentation-redis==0.50b0',
        'opentelemetry-instrumentation-remoulade==0.50b0',
        'opentelemetry-instrumentation-requests==0.50b0',
        'opentelemetry-instrumentation-sqlalchemy==0.50b0',
        'opentelemetry-instrumentation-sqlite3==0.50b0',
        'opentelemetry-instrumentation-starlette==0.50b0',
        'opentelemetry-instrumentation-tornado==0.50b0',
        'opentelemetry-instrumentation-tortoiseorm==0.50b0',
        'opentelemetry-instrumentation-threading==0.50b0',
        'opentelemetry-instrumentation-urllib==0.50b0',
        'opentelemetry-instrumentation-urllib3==0.50b0',
        'opentelemetry-instrumentation-wsgi==0.50b0',
        'setuptools==75.3.0'
    ],
    python_requires=">=3.8",
)