"""Unit tests for BM25 In-Memory Search Engine."""

import pytest
from gravitypress.core.parser import MarkdownParser
from gravitypress.core.search import BM25SearchEngine


def test_bm25_search_indexing_and_ranking():
    parser = MarkdownParser()
    doc1 = parser.parse_text("""---
title: "Kubernetes Container Orchestration"
category: "DevOps"
---
Kubernetes automates deployment, scaling, and management of containerized applications.
""")

    doc2 = parser.parse_text("""---
title: "Python Asynchronous Programming"
category: "Engineering"
---
Asyncio is a library to write concurrent code using the async and await syntax in Python.
""")

    searcher = BM25SearchEngine()
    searcher.build_index([doc1, doc2])

    # Search for Python
    res_py = searcher.search("Python")
    assert len(res_py) > 0
    assert res_py[0].document.metadata.title == "Python Asynchronous Programming"
    assert "python" in res_py[0].matched_terms

    # Search for Kubernetes
    res_k8s = searcher.search("Kubernetes")
    assert len(res_k8s) > 0
    assert res_k8s[0].document.metadata.title == "Kubernetes Container Orchestration"
