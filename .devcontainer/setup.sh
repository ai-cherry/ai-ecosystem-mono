#!/bin/bash
set -euo pipefail

echo "🧪 Checking Python and Node..."
python3 --version
node --version || echo "⚠️ Node is missing — you may want to install it or use a devcontainer with node feature"

# Step 1: Install pipx safely
echo "🔧 Installing pipx..."
python3 -m pip install --quiet --user pipx
python3 -m pipx ensurepath

# Step 2: Install Poetry and PNPM (safe re-install)
echo "🔧 Installing Poetry and PNPM..."
pipx install poetry || echo "✔️ Poetry already installed"
npm install -g pnpm || echo "✔️ PNPM already installed"

# Step 3: Bootstrap monorepo (recursive app/package setup)
ROOT_DIR="/workspaces/ai-ecosystem-mono"

echo "📦 Installing Python deps in /apps and /packages..."
find "$ROOT_DIR/apps" "$ROOT_DIR/packages" -name "pyproject.toml" \
  -execdir poetry install --no-interaction --no-root \;

echo "📦 Installing JS deps in /apps and /packages..."
find "$ROOT_DIR/apps" "$ROOT_DIR/packages" -name "package.json" \
  -execdir pnpm install \;

# Step 4: Pre-commit, just in case
if [ -f "$ROOT_DIR/.pre-commit-config.yaml" ]; then
  echo "✅ Installing pre-commit hooks..."
  pipx install pre-commit || echo "✔️ Pre-commit already installed"
  pre-commit install
fi

# Step 5: Optional — seed .env if it doesn’t exist
if [ ! -f "$ROOT_DIR/.env" ] && [ -f "$ROOT_DIR/.env.example" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "📄 Copied .env from .env.example"
fi

echo "✅ Dev environment ready to go!"
