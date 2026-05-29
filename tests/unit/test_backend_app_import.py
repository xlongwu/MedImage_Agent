"""Smoke test: verify the backend app can be imported and has expected shape."""

from __future__ import annotations

from fastapi import FastAPI


def test_app_imports():
    """The FastAPI app must be importable from its expected module path."""
    from src.backend.app.main import app
    assert isinstance(app, FastAPI)


def test_app_has_title():
    from src.backend.app.main import app
    assert app.title is not None
    assert len(app.title) > 0


def test_app_has_routes():
    """App should have at least the /health route."""
    from src.backend.app.main import app
    route_paths = [r.path for r in app.routes]
    assert "/health" in route_paths, f"Expected /health in routes, got {route_paths}"
