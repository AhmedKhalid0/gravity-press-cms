"""Unit tests for Markdown AST Parser and Frontmatter Extractor."""

import pytest
from gravitypress.core.parser import MarkdownParser


def test_parse_frontmatter_and_markdown():
    raw_md = """---
title: "Modern Microservices with Python"
slug: "modern-microservices"
category: "Engineering"
tags:
  - Python
  - Architecture
excerpt: "A deep dive into microservices."
status: "PUBLISHED"
---

## Section One

This is a test paragraph with **bold text** and `inline code`.

### Subsection

* Item 1
* Item 2
"""
    parser = MarkdownParser()
    doc = parser.parse_text(raw_md)

    assert doc.metadata.title == "Modern Microservices with Python"
    assert doc.metadata.slug == "modern-microservices"
    assert doc.metadata.category == "Engineering"
    assert "Python" in doc.metadata.tags
    assert doc.metadata.status == "PUBLISHED"
    assert doc.word_count > 10
    assert doc.reading_time_minutes >= 1
    assert "<h2>Section One</h2>" in doc.html_content or "<h2 id=" in doc.html_content
    assert "<strong>bold text</strong>" in doc.html_content


def test_slugify_fallback():
    raw_md = """---
title: "Zero-Latency Edge APIs!"
---

Content body.
"""
    parser = MarkdownParser()
    doc = parser.parse_text(raw_md)

    assert doc.metadata.slug == "zero-latency-edge-apis"
    assert doc.metadata.category == "Technology"
