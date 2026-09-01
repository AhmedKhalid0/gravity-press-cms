"""Unit tests for SEO and OpenGraph Analyzer."""

import pytest
from gravitypress.core.seo import SEOAnalyzer


def test_seo_analyzer_scores():
    title = "Architecting High-Performance Microservices in Python"
    desc = "A comprehensive deep dive into building ultra-low latency, decoupled microservices with Python and FastAPI."
    body = """## Overview

Microservices enable decoupled scaling and isolation.

### Key Considerations

* Resilience
* Observability
* Distributed Tracing
"""
    result = SEOAnalyzer.analyze(
        title=title,
        description=desc,
        markdown_body=body,
        featured_image="https://example.com/banner.jpg",
        author_name="Ahmed Khaled",
    )

    assert result.score >= 70
    assert result.grade in ["Excellent", "Good"]
    assert result.open_graph_tags["og:title"] == title
    assert result.open_graph_tags["twitter:card"] == "summary_large_image"
