"""Integration tests for FastAPI REST API endpoints."""

import pytest
from fastapi.testclient import TestClient
from gravitypress.main import app

client = TestClient(app)


def test_health_check_endpoint():
    res = client.get("/api/v1/health/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["engine"] == "GravityPress CMS"


def test_list_articles_endpoint():
    res = client.get("/api/v1/content/articles/")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "articles" in data
    assert len(data["articles"]) > 0


def test_get_article_detail_endpoint():
    res_list = client.get("/api/v1/content/articles/")
    first_slug = res_list.json()["articles"][0]["slug"]

    res_detail = client.get(f"/api/v1/content/articles/{first_slug}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["metadata"]["slug"] == first_slug
    assert "html_content" in detail
    assert "seo_score" in detail


def test_search_endpoint():
    res = client.get("/api/v1/content/search?q=Python")
    assert res.status_code == 200
    data = res.json()
    assert data["query"] == "Python"
    assert "results" in data
