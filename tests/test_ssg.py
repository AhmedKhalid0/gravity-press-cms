"""Unit tests for Static Site Generator (SSG), Sitemap, RSS, and Cloudflare manifests."""

import shutil
from pathlib import Path
import pytest
from gravitypress.core.ssg import StaticSiteGenerator


def test_ssg_build_pipeline():
    test_root = Path("tests/temp_test_ssg")
    if test_root.exists():
        shutil.rmtree(test_root)

    content_dir = test_root / "content" / "articles"
    content_dir.mkdir(parents=True)
    out_dir = test_root / "dist"

    test_art = content_dir / "test-post.md"
    test_art.write_text("""---
title: "SSG Compilation Test Article"
slug: "ssg-test-article"
category: "Testing"
status: "PUBLISHED"
---
## Test Heading

Hello from SSG test suite!
""", encoding="utf-8")

    try:
        ssg = StaticSiteGenerator(content_dir=test_root / "content", output_dir=out_dir)
        res = ssg.build()

        assert res["status"] == "success"
        assert res["articles_count"] == 1

        # Verify generated files
        assert (out_dir / "index.html").exists()
        assert (out_dir / "articles" / "ssg-test-article" / "index.html").exists()
        assert (out_dir / "sitemap.xml").exists()
        assert (out_dir / "feed.xml").exists()
        assert (out_dir / "_headers").exists()
        assert (out_dir / "_redirects").exists()

        # Verify content in generated article
        art_html = (out_dir / "articles" / "ssg-test-article" / "index.html").read_text(encoding="utf-8")
        assert "SSG Compilation Test Article" in art_html
        assert "Hello from SSG test suite!" in art_html
    finally:
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)
