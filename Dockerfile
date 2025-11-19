# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install --upgrade pip wheel
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8000"]