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

# Install Rust toolchain and cross targets early in build
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable && \
    /root/.cargo/bin/rustup target add \
        x86_64-unknown-linux-gnu \
        x86_64-apple-darwin \
        x86_64-pc-windows-gnu

ENV \
    REPO_URL="https://github.com/r3dwh33lbarrow/onewAy.git" \
    REPO_REF="main" \
    PROJECT_DIR="/workspace/oneway" \
    POSTGRES_HOST="oneway-db" \
    POSTGRES_PORT="5432" \
    POSTGRES_DB="oneway" \
    POSTGRES_USER="onewayuser" \
    BACKEND_PORT="8000" \
    FRONTEND_PORT="5173" \
    CLIENT_VERSION="0.1.0" \
    PYTHONPATH="/workspace/oneway/server/backend" \
    PATH="/root/.cargo/bin:${PATH}" \
    SECRETS_DIR="/workspace/.secrets"

# Create secrets directory with restrictive permissions
RUN mkdir -p "${SECRETS_DIR}" && chmod 700 "${SECRETS_DIR}"

RUN python -m pip install --upgrade pip setuptools wheel

COPY docker/start-services.sh /usr/local/bin/start-services.sh
RUN chmod +x /usr/local/bin/start-services.sh

LABEL org.opencontainers.image.title="onewAy" \
      org.opencontainers.image.description="Docker image that boots the onewAy backend, frontend, and supporting services" \
      org.opencontainers.image.source="https://github.com/r3dwh33lbarrow/onewAy" \
      org.opencontainers.image.authors="onewAy Maintainers"

ENTRYPOINT ["/usr/local/bin/start-services.sh"]