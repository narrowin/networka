# syntax=docker/dockerfile:1.7-labs
ARG PYTHON_VERSION=3.12.7

FROM python:${PYTHON_VERSION}-slim-bookworm

# Install system dependencies without pinned versions (versions change frequently)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    openssh-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && mkdir -p /home/$USERNAME/.cache/pip /home/$USERNAME/.cache/uv \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME

# Install uv with pinned version
ENV UV_VERSION=0.4.18
RUN curl -LsSf https://astral.sh/uv/$UV_VERSION/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy uv binary to system location for all users
RUN cp /root/.local/bin/uv /usr/local/bin/uv

# Create workspace directory
RUN mkdir -p /workspace && chown $USERNAME:$USERNAME /workspace

# Create writable directories for volumes
RUN mkdir -p /workspace/.venv /workspace/outputs /workspace/test_results /workspace/results \
    && chown -R $USERNAME:$USERNAME /workspace

# Switch to non-root user
USER $USERNAME

# Set working directory
WORKDIR /workspace

# Verify installation
RUN python --version && uv --version

# Set default command
CMD ["/bin/bash"]
