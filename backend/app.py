from __future__ import annotations

import sys
import types
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent

# Vercel may execute this file as /var/task/app.py, where the original
# "backend" package name is no longer importable. Register a lightweight
# package alias so backend.main and its relative imports still resolve.
if "backend" not in sys.modules:
    backend_package = types.ModuleType("backend")
    backend_package.__path__ = [str(CURRENT_DIR)]
    sys.modules["backend"] = backend_package

from backend.main import app, create_app

__all__ = ["app", "create_app"]
