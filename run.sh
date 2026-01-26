#!/bin/bash
# Force run with arm64 architecture on Apple Silicon
cd "$(dirname "$0")"
arch -arm64 venv/bin/python -m src.main "$@"
