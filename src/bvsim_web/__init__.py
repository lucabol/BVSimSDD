"""Flask web interface for BVSim.

This package provides a minimal web UI and JSON API to expose BVSim functionality
without modifying existing simulator code. It imports and reuses the internal
Python APIs instead of invoking the CLI layer.
"""
from __future__ import annotations
from flask import Flask
from .app import register_routes


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    register_routes(app)
    return app
