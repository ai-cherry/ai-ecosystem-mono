#!/bin/bash
set -euo pipefail # Keep this!

echo "✅ Running post-create setup..."

# Optional checks (tools should exist now)
echo "🧪 Checking core tools..."
python3 --version
poetry --version || (echo "❌ Poetry not found!" && exit 1)
node --version || echo "⚠️ Node not found (install if needed)"
pnpm --version || (echo "❌ PNPM not found! Install Node/PNPM globally." && exit 1)
pre-commit --version || (echo "❌ pre-commit not found!" && exit 1)


# Step 1: Install monorepo dependencies
ROOT_DIR="/workspaces/ai-ecosystem-mono" # Standard Codespaces path

echo "📦 Installing Python deps in /apps and /packages..."
find "$ROOT_DIR/apps" "$ROOT_DIR/packages" -name "pyproject.toml" -print -execdir poetry install --no-interaction --no-root \;
echo "🐍 Python dependencies installed."

echo "📦 Installing JS deps in /apps and /packages..."
find "$ROOT_DIR/apps" "$ROOT_DIR/packages" -name "package.json" -print -execdir pnpm install \;
echo "📜 JS dependencies installed."


# Step 2: Install pre-commit hooks
if [ -f "$ROOT_DIR/.pre-commit-config.yaml" ]; then
  echo " Git hook setup..."
  # Ensure we are in the root, pre-commit needs to find .git
  cd "$ROOT_DIR"
  pre-commit install
  echo "✅ Pre-commit hooks installed."
else
    echo "⏭️ No .pre-commit-config.yaml found, skipping hook installation."
fi

# Step 3: Optional — seed .env if it doesn’t exist
if [ ! -f "$ROOT_DIR/.env" ] && [ -f "$ROOT_DIR/.env.example" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "📄 Copied .env from .env.example"
fi

echo "🎉 Dev environment ready to go!"
