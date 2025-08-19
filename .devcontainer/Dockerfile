# syntax=docker/dockerfile:1.7-labs
ARG PYTHON_VERSION=3.12.7

FROM python:${PYTHON_VERSION}-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    openssh-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install pipx and uv
RUN python -m pip install --no-cache-dir pipx \
    && python -m pipx install uv \
    && python -m pipx ensurepath

# Create non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && mkdir -p /home/$USERNAME/.cache/pip /home/$USERNAME/.cache/uv \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME

# Create workspace directory
RUN mkdir -p /workspace && chown $USERNAME:$USERNAME /workspace

# Create writable directories for volumes
RUN mkdir -p /workspace/.venv /workspace/outputs /workspace/test_results /workspace/results \
    && chown -R $USERNAME:$USERNAME /workspace

# Switch to non-root user
USER $USERNAME

# Add pipx bin to PATH for user
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /workspace

# Set default command
CMD ["/bin/bash"]
