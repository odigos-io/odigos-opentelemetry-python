ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

COPY tests/integration/apps/django-app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tests/integration/apps/django-app/ .

ENV DJANGO_SETTINGS_MODULE=settings

EXPOSE 8080

CMD ["gunicorn", "wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "3"]
