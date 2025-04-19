# Base Image: Python 3.11 Dev Container with common build tools
FROM mcr.microsoft.com/devcontainers/python:3.11

# Install base system packages (Your existing list, e.g., git, redis-tools, etc.)
# RUN apt-get update && export DEBIAN_FRONTEND=noninteractive && apt-get install -y --no-install-recommends <your_packages> && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- NEW: Install pipx and core Python tools ---
USER root
RUN python3 -m pip install --no-cache-dir pipx \
    && pipx ensurepath \
    && pipx install --pip-args="--no-cache-dir" poetry \
    && pipx install --pip-args="--no-cache-dir" pre-commit

# Ensure pipx path is available for all users (including vscode later)
# This might need adjustment based on exact base image setup, but often works:
RUN echo 'export PATH="$PATH:/root/.local/bin"' >> /etc/bash.bashrc \
    && echo 'export PATH="$PATH:/root/.local/bin"' >> /etc/profile.d/pipx.sh \
    && chmod +x /etc/profile.d/pipx.sh
# Alternatively, specifically add to vscode user's PATH if needed after user creation below

# --- Node.js/PNPM Installation ---
# Option A: Keep the Dev Container Feature for Node in devcontainer.json (Recommended)
# Option B: Install manually here if not using the feature
# RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
#    && apt-get install -y nodejs \
#    && npm install -g pnpm

# --- Other installations (GCloud, Terraform) ---
# Keep your existing RUN commands for gcloud/terraform, but fix apt-key warning
# Example Fix for Terraform (adjust repo details if needed):
RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list > /dev/null \
    && apt-get update && apt-get install -y terraform

# [Your existing COPY commands, USER vscode setup, HEALTHCHECK etc.]
# If HEALTHCHECK exists, make it meaningful: HEALTHCHECK CMD ["poetry", "--version"] || exit 1
