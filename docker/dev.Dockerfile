# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS base

# --- System setup ---
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libpq-dev \
    postgresql-client \
    netcat-openbsd \
    libmagic-dev \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

ENV \
    REPO_URL="https://github.com/r3dwh33lbarrow/onewAy.git" \
    REPO_REF="main" \
    PROJECT_DIR="/workspace/oneway" \
    POSTGRES_HOST="db" \
    POSTGRES_PORT="5432" \
    POSTGRES_DB="oneway" \
    POSTGRES_USER="onewayuser" \
    POSTGRES_PASSWORD="onewaypass" \
    BACKEND_PORT="8000" \
    FRONTEND_PORT="5173" \
    CLIENT_VERSION="0.1.0" \
    SECURITY_SECRET_KEY="dev-secret" \
    PYTHONPATH="/workspace/oneway/server/backend" \
    PATH="/root/.cargo/bin:${PATH}"

RUN python -m pip install --upgrade pip setuptools wheel

COPY docker/start-services.sh /usr/local/bin/start-services.sh
RUN chmod +x /usr/local/bin/start-services.sh

# Install Rust toolchain and cross targets
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable && \
    /root/.cargo/bin/rustup target add \
        x86_64-unknown-linux-gnu \
        x86_64-apple-darwin \
        x86_64-pc-windows-gnu

ENTRYPOINT ["/usr/local/bin/start-services.sh"]
