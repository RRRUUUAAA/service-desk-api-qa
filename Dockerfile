# syntax=docker/dockerfile:1.7
FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.lock ./
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
    --index-url "${PIP_INDEX_URL}" \
    -r requirements.lock

COPY app ./app
COPY tests ./tests
COPY pytest.ini ./

RUN mkdir -p /app/reports

EXPOSE 8000
