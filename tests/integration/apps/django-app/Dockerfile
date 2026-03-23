ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY tests/integration/apps/django-app/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY tests/integration/apps/django-app/ .

ENV DJANGO_SETTINGS_MODULE=settings

EXPOSE 8080

CMD ["gunicorn", "wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "3"]
