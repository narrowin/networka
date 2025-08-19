FROM python:3.12-slim

RUN apt-get update && apt-get install -y git ssh && rm -rf /var/lib/apt/lists/*
RUN pip install uv
RUN useradd -m -s /bin/bash vscode

USER vscode
WORKDIR /workspace
