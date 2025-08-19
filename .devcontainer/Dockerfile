FROM python:3.12-slim

# Install essential system packages and networking tools
RUN apt-get update && apt-get install -y \
    # Essential development tools
    git \
    ssh \
    curl \
    wget \
    # Networking tools
    iputils-ping \
    traceroute \
    telnet \
    netcat-openbsd \
    nmap \
    tcpdump \
    net-tools \
    iproute2 \
    dnsutils \
    whois \
    mtr-tiny \
    iperf3 \
    netstat-nat \
    socat \
    # Additional utilities
    jq \
    vim \
    nano \
    less \
    htop \
    tree \
    unzip \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# Install atuin (shell history) as root first
RUN curl --proto '=https' --tlsv1.2 -sSf https://setup.atuin.sh | bash

RUN pip install uv
RUN useradd -m -s /bin/bash vscode

# Copy atuin binary to system location so it's available for all users
RUN cp /root/.cargo/bin/atuin /usr/local/bin/atuin

USER vscode
WORKDIR /workspace

# Setup atuin for the vscode user - will be done in post-create script
# to ensure proper configuration with persistent volumes
