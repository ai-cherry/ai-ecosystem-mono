#!/bin/bash
set -e

# Install pipx
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install Poetry and PNPM
echo "🔧 Installing Poetry and PNPM..."
pipx install poetry || echo "Poetry already installed"
npm install -g pnpm || echo "PNPM already installed"

# Install dependencies in /apps and /packages
echo "📦 Installing dependencies in /apps and /packages..."
find /workspaces/ai-ecosystem-mono/apps /workspaces/ai-ecosystem-mono/packages -name "pyproject.toml" -execdir poetry install \;
find /workspaces/ai-ecosystem-mono/apps /workspaces/ai-ecosystem-mono/packages -name "package.json" -execdir pnpm install \;

echo "✅ Dev environment ready."
