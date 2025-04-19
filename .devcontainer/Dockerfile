FROM mcr.microsoft.com/devcontainers/python:3.11

# Install additional dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        curl gnupg lsb-release \
        redis-tools \
        docker.io \
        bash-completion \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Google Cloud SDK
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | \
    tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
    apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - && \
    apt-get update && apt-get install -y google-cloud-sdk

# Install Terraform
RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | apt-key add - \
    && apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
    && apt-get update && apt-get install -y terraform

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Pre-install Python dependencies
COPY orchestrator-requirements.txt /tmp/orchestrator-requirements.txt
COPY shared-requirements.txt /tmp/shared-requirements.txt

# Install Python dependencies, including development tools
RUN pip install --no-cache-dir -r /tmp/orchestrator-requirements.txt && \
    pip install --no-cache-dir -r /tmp/shared-requirements.txt && \
    pip install --no-cache-dir pytest pytest-cov black flake8 isort mypy pre-commit temporalio
