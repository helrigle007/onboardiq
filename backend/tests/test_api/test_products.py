"""Tests for product API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_products_returns_stripe(client):
    """GET /api/products/ returns Stripe in the product list."""
    response = await client.get("/api/products/")
    assert response.status_code == 200
    data = response.json()
    assert "products" in data
    products = data["products"]
    assert len(products) >= 1
    stripe = next(p for p in products if p["id"] == "stripe")
    assert stripe["name"] == "Stripe"
    assert stripe["doc_count"] == 6


@pytest.mark.asyncio
async def test_get_product_stripe(client):
    """GET /api/products/stripe returns product info."""
    response = await client.get("/api/products/stripe")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "stripe"
    assert data["name"] == "Stripe"
    assert "available_roles" in data
    assert len(data["available_roles"]) == 6


@pytest.mark.asyncio
async def test_get_product_unknown_returns_404(client):
    """GET /api/products/unknown returns 404."""
    response = await client.get("/api/products/unknown")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"
