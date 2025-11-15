#!/bin/bash
set -e

echo "🚀 Initializing development environment..."

echo "🔧 Installing dependencies..."
curl -LsSf https://astral.sh/uv/install.sh | sh

echo "📦 Setting up uv..."
cd backend
uv sync

echo "🔧 Setting up pre-commit hooks..."
cd ..
pip install pre-commit
pre-commit install
pre-commit autoupdate

echo "✅ Development environment setup complete!"
