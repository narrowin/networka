FROM python:3.11-slim

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install system packages and network debugging tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    openssh-client \
    openssh-server \
    iputils-ping \
    traceroute \
    tcpdump \
    nmap \
    netcat-openbsd \
    dnsutils \
    iproute2 \
    net-tools \
    mtr-tiny \
    curl \
    wget \
    whois \
    arp-scan \
    sudo \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# Create networka user and give sudo access
RUN useradd -m -s /bin/bash networka && \
    echo 'networka:networka' | chpasswd && \
    usermod -aG sudo networka && \
    echo 'networka ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Configure SSH
RUN mkdir -p /var/run/sshd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config && \
    echo 'UseDNS no' >> /etc/ssh/sshd_config && \
    echo 'PermitEmptyPasswords no' >> /etc/ssh/sshd_config

# Create app directory and set permissions
WORKDIR /app
RUN mkdir -p /app/data && chown -R networka:networka /app

# Copy project files and set ownership
COPY . .
RUN chown -R networka:networka /app

# Switch to networka user for installation
USER networka

# Install networka as networka user
RUN uv tool install .

# Set PATH for networka user
ENV PATH="/home/networka/.local/bin:$PATH"
RUN echo 'export PATH="/home/networka/.local/bin:$PATH"' >> /home/networka/.bashrc && \
    echo 'export PATH="/home/networka/.local/bin:$PATH"' >> /home/networka/.profile

# Setup SSH directory
RUN mkdir -p /home/networka/.ssh && chmod 700 /home/networka/.ssh

# Verify installation works
RUN nw --help

# Switch back to root for service setup
USER root

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose SSH port
EXPOSE 22

# Declare data volume
VOLUME ["/app/data"]

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
