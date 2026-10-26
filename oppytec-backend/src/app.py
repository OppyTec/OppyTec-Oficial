"""
oppytec-backend/src/app.py
Punto de entrada de la aplicación FastAPI principal para ASGI y tests.
"""
from __future__ import annotations

from src.main import app, create_app

__all__ = ["app", "create_app"]
