#!/bin/bash

python3 script.py
/app/venv/bin/gunicorn -w 5 -k uvicorn.workers.UvicornWorker main:app -b 0.0.0.0:8000
