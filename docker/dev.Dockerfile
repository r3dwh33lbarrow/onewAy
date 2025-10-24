# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS base

# --- System setup ---
ENV DEBIAN_FRONTEND=noninteractive
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    if [ "$arch" = "arm64" ]; then \
        dpkg --add-architecture amd64; \
    fi; \
    apt-get update; \
    apt-get install -y \
        ca-certificates \
        curl \
        git \
        build-essential \
        pkg-config \
        libssl-dev \
        zlib1g-dev \
        libpq-dev \
        postgresql-client \
        netcat-openbsd \
        libmagic-dev \
        npm \
        clang \
        lld \
        llvm \
        cmake \
        autoconf \
        automake \
        bison \
        flex \
        ninja-build \
        unzip \
        zip \
        xz-utils \
        cpio \
        procps \
        mingw-w64 \
        gcc-mingw-w64-x86-64 \
        g++-mingw-w64-x86-64 \
        uuid-dev \
        libxml2-dev \
        libbz2-dev \
        liblzma-dev \
        patchelf \
        rsync; \
    if [ "$arch" = "arm64" ]; then \
        apt-get install -y \
            gcc-x86-64-linux-gnu \
            g++-x86-64-linux-gnu \
            binutils-x86-64-linux-gnu \
            libssl-dev:amd64 \
            zlib1g-dev:amd64 \
            libxml2-dev:amd64 \
            libbz2-dev:amd64 \
            liblzma-dev:amd64; \
    fi; \
    if update-alternatives --query x86_64-w64-mingw32-gcc >/dev/null 2>&1; then \
        update-alternatives --set x86_64-w64-mingw32-gcc /usr/bin/x86_64-w64-mingw32-gcc-posix; \
    fi; \
    if update-alternatives --query x86_64-w64-mingw32-g++ >/dev/null 2>&1; then \
        update-alternatives --set x86_64-w64-mingw32-g++ /usr/bin/x86_64-w64-mingw32-g++-posix; \
    fi; \
    ln -sf /usr/bin/pkg-config /usr/bin/x86_64-linux-gnu-pkg-config; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install Rust toolchain and cross targets early in build
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable && \
    /root/.cargo/bin/rustup target add \
        x86_64-unknown-linux-gnu \
        x86_64-apple-darwin \
        x86_64-pc-windows-gnu

ARG OSX_SDK_VERSION=12.3
ARG OSX_SDK_DOWNLOAD=https://github.com/phracker/MacOSX-SDKs/releases/download/${OSX_SDK_VERSION}/MacOSX${OSX_SDK_VERSION}.sdk.tar.xz
ENV MACOSX_DEPLOYMENT_TARGET=10.13
RUN set -eux; \
    git clone --depth 1 https://github.com/tpoechtrager/osxcross.git /opt/osxcross; \
    curl -L -o /tmp/MacOSX${OSX_SDK_VERSION}.sdk.tar.xz "${OSX_SDK_DOWNLOAD}"; \
    mv /tmp/MacOSX${OSX_SDK_VERSION}.sdk.tar.xz /opt/osxcross/tarballs/; \
    UNATTENDED=1 OSX_VERSION_MIN=${MACOSX_DEPLOYMENT_TARGET} /opt/osxcross/build.sh; \
    rm -rf /opt/osxcross/build /opt/osxcross/.git /opt/osxcross/tarballs/MacOSX${OSX_SDK_VERSION}.sdk.tar.xz

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
    PATH="/opt/osxcross/target/bin:/root/.cargo/bin:${PATH}" \
    SECRETS_DIR="/workspace/.secrets"

ENV OSX_SDK_VERSION=${OSX_SDK_VERSION}
ENV \
    PKG_CONFIG_ALLOW_CROSS=1 \
    PKG_CONFIG_x86_64_unknown_linux_gnu=/usr/bin/pkg-config \
    PKG_CONFIG_LIBDIR_x86_64_unknown_linux_gnu=/usr/lib/x86_64-linux-gnu/pkgconfig \
    PKG_CONFIG_SYSROOT_DIR_x86_64_unknown_linux_gnu=/ \
    OPENSSL_DIR_x86_64_unknown_linux_gnu=/usr/lib/x86_64-linux-gnu \
    OPENSSL_LIB_DIR_x86_64_unknown_linux_gnu=/usr/lib/x86_64-linux-gnu \
    OPENSSL_INCLUDE_DIR_x86_64_unknown_linux_gnu=/usr/include/x86_64-linux-gnu \
    CC_x86_64_unknown_linux_gnu=x86_64-linux-gnu-gcc \
    CXX_x86_64_unknown_linux_gnu=x86_64-linux-gnu-g++ \
    AR_x86_64_unknown_linux_gnu=x86_64-linux-gnu-ar \
    CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER=x86_64-linux-gnu-gcc \
    CC_x86_64_pc_windows_gnu=x86_64-w64-mingw32-gcc \
    CXX_x86_64_pc_windows_gnu=x86_64-w64-mingw32-g++ \
    AR_x86_64_pc_windows_gnu=x86_64-w64-mingw32-ar \
    RANLIB_x86_64_pc_windows_gnu=x86_64-w64-mingw32-ranlib \
    CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER=x86_64-w64-mingw32-gcc \
    CC_x86_64_apple_darwin=o64-clang \
    CXX_x86_64_apple_darwin=o64-clang++ \
    AR_x86_64_apple_darwin=x86_64-apple-darwin-ar \
    RANLIB_x86_64_apple_darwin=x86_64-apple-darwin-ranlib \
    CARGO_TARGET_X86_64_APPLE_DARWIN_LINKER=o64-clang \
    CARGO_TARGET_X86_64_APPLE_DARWIN_AR=x86_64-apple-darwin-ar \
    SDKROOT=/opt/osxcross/target/SDK/MacOSX${OSX_SDK_VERSION}.sdk

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
