"""Shim: run with `uvicorn api:app --app-dir src` from the project root."""
from badminton.presentation.api.app import app  # noqa: F401