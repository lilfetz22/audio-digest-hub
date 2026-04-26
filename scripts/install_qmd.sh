#!/usr/bin/env sh
set -eu

if command -v qmd >/dev/null 2>&1; then
  echo "qmd is already installed: $(qmd --version)"
  exit 0
fi

echo "Installing qmd..."
npm install -g @tobilu/qmd
qmd --version
