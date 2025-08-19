# syntax=docker/dockerfile:1.7
ARG VARIANT=3.12
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}

ARG UID=1000
ARG GID=1000

# Minimal but complete dev/debug toolchain + cargo deps for Atuin
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates git curl wget \
    build-essential pkg-config \
    openssh-client iputils-ping \
    traceroute telnet netcat-openbsd nmap tcpdump net-tools iproute2 dnsutils whois mtr-tiny iperf3 socat \
    jq vim nano less htop tree unzip tmux; \
    rm -rf /var/lib/apt/lists/*

# Security: container shells won't persist history
ENV HISTFILE=/dev/null

# Workspace-independent persistent dirs
ENV WORKDATA=/workdata
ENV XDG_CACHE_HOME=${WORKDATA}/cache
ENV XDG_CONFIG_HOME=${WORKDATA}/config
ENV XDG_STATE_HOME=${WORKDATA}/state
ENV XDG_DATA_HOME=${WORKDATA}/data
ENV PIP_CACHE_DIR=${XDG_CACHE_HOME}/pip
ENV UV_CACHE_DIR=${XDG_CACHE_HOME}/uv

# Results default away from workspace (read-only bind)
ENV NW_RESULTS_DIR=${WORKDATA}/results

# Python virtualenv in persistent storage
ENV VIRTUAL_ENV=${WORKDATA}/venv
ENV PATH=${VIRTUAL_ENV}/bin:/home/vscode/.cargo/bin:${PATH}

# Prepare persistent layout
RUN mkdir -p ${WORKDATA}/venv ${WORKDATA}/cache ${WORKDATA}/results ${WORKDATA}/test_results ${WORKDATA}/config/bash \
    && chown -R vscode:vscode ${WORKDATA} /home/vscode

USER vscode

# Create venv and basic tooling (uv via pip here for simplicity)
RUN python -m venv ${VIRTUAL_ENV} \
    && pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir uv ipykernel pytest pytest-asyncio ruff mypy

# Install Atuin via official installer
RUN curl --proto '=https' --tlsv1.2 -sSf https://setup.atuin.sh | bash

WORKDIR /workspace
