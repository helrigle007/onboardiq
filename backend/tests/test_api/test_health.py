"""Tests for health check endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_check_returns_200(client):
    """GET /api/health returns 200."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_includes_models(client):
    """GET /api/health includes model names."""
    response = await client.get("/api/health")
    data = response.json()
    assert "models" in data
    models = data["models"]
    assert "generation" in models
    assert "evaluation" in models
    assert "fast" in models
