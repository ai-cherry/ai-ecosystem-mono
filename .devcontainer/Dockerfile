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
# Note: Using apt-key add is deprecated, but following original file for now.
# Consider updating to the recommended signed-by method if issues arise.
RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | apt-key add - && \
  apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main" && \
  apt-get update && apt-get install -y terraform

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Keep this Poetry setting if your setup.sh relies on it
    POETRY_VIRTUALENVS_IN_PROJECT=true

# Install Poetry and common Python dev tools globally
# REMOVED installation from requirements.txt
# ADDED Poetry installation
RUN pip install --no-cache-dir \
      poetry \
      pytest pytest-cov \
      black flake8 isort mypy \
      pre-commit temporalio

# Add `vscode` user so Codespaces can run as non-root
# Ensure tools installed above are accessible to this user (they should be in global site-packages or PATH)
RUN useradd -m vscode && \
    echo 'vscode ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers.d/99-vscode && \
    chown -R vscode:vscode /home/vscode

# Optional: Healthcheck to indicate successful startup
HEALTHCHECK CMD python -c "import sys; sys.exit(0 if True else 1)"

# Note: Project-specific dependencies (like langchain, pydantic, etc.)
# should now be installed via Poetry in your setup.sh script (postCreateCommand)
# after the container is built and the source code is mounted.
