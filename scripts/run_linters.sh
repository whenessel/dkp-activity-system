#!/usr/bin/env bash
poetry run isort src --profile black
poetry run ruff src --fix
poetry run black src

# CHECKS
poetry run isort src --profile black --check-only
poetry run black src --check
poetry run ruff check src
poetry run flake8 src

#poetry run mypy src
