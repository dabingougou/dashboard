#!/usr/bin/env bash
# Recreate the Python environment for this repo on a fresh machine (e.g. a
# Raspberry Pi) after `git clone`. Safe to re-run. Needs no sudo: it only
# touches files inside the repo.
#
# Prerequisites (normally present on Raspberry Pi OS): python3 (3.9+),
# python3-venv, git. Optional: fonts-dejavu-core for the nicest PNG text
# (a built in Pillow font is used otherwise).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

if [ ! -d .venv ]; then
  echo "Creating virtual environment in .venv"
  python3 -m venv .venv
fi

echo "Installing requirements"
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

if [ ! -f config.yaml ]; then
  cp config.example.yaml config.yaml
  chmod 600 config.yaml
  echo "Created config.yaml from config.example.yaml; fill in any secrets there."
else
  echo "config.yaml already exists; left unchanged."
fi

echo "Done. Try: .venv/bin/python run.py sample"
