"""Integration tests for Strawberry GraphQL queries and schema execution."""

import pytest
from fastapi.testclient import TestClient
from gravitypress.main import app

client = TestClient(app)


def test_graphql_site_metadata():
    query = """
    query {
      siteMetadata {
        title
        engine
        version
        totalArticles
      }
    }
    """
    res = client.post("/graphql", json={"query": query})
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    meta = data["data"]["siteMetadata"]
    assert meta["title"] == "GravityPress CMS"
    assert meta["totalArticles"] >= 3


def test_graphql_articles_query():
    query = """
    query {
      articles(limit: 2) {
        title
        slug
        category
        readingTimeMinutes
        author {
          name
        }
      }
    }
    """
    res = client.post("/graphql", json={"query": query})
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    articles = data["data"]["articles"]
    assert len(articles) <= 2
    assert "title" in articles[0]
    assert "author" in articles[0]
