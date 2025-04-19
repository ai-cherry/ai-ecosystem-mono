# Base image: Python 3.11 Dev Container with common build tools
FROM mcr.microsoft.com/devcontainers/python:3.11

# Install base system packages (REMOVED docker.io)
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
  && apt-get -y install --no-install-recommends \
    curl gnupg lsb-release \
    redis-tools \
    bash-completion \
    git \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install Google Cloud SDK
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
  | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
  curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - && \
  apt-get update && apt-get install -y google-cloud-sdk

# Install Terraform
RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | apt-key add - && \
  apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main" && \
  apt-get update && apt-get install -y terraform

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # This needs to be set *before* setup.sh runs poetry install
    POETRY_VIRTUALENVS_IN_PROJECT=true

# Install pipx (which setup.sh will use to install poetry, pre-commit)
# REMOVED global pip install of poetry, pytest, black, flake8, etc.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir pipx

# Add `vscode` user so Codespaces can run as non-root
RUN useradd -m vscode && \
    echo 'vscode ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers.d/99-vscode && \
    chown -R vscode:vscode /home/vscode

# Optional: Healthcheck
HEALTHCHECK CMD python -c "import sys; sys.exit(0 if True else 1)"

# Note: Project dependencies AND core Python dev tools (poetry, pre-commit)
# are now installed by setup.sh using pipx and poetry install.
