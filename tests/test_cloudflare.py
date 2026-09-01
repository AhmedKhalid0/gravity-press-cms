"""Unit tests for Cloudflare Pages integration and manifests."""

import shutil
from pathlib import Path
import pytest
from gravitypress.core.cloudflare import CloudflareConfig, CloudflareEdgeManager


def test_cloudflare_manifests_generation():
    test_root = Path("tests/temp_test_cf")
    if test_root.exists():
        shutil.rmtree(test_root)

    out_dir = test_root / "dist"
    cf_manager = CloudflareEdgeManager(CloudflareConfig())

    try:
        cf_manager.generate_edge_manifests(out_dir)

        headers_file = out_dir / "_headers"
        redirects_file = out_dir / "_redirects"

        assert headers_file.exists()
        assert redirects_file.exists()

        headers_text = headers_file.read_text(encoding="utf-8")
        assert "Cache-Control: public, max-age=31536000, immutable" in headers_text
        assert "X-Frame-Options: DENY" in headers_text

        redirects_text = redirects_file.read_text(encoding="utf-8")
        assert "/admin        /admin/           301" in redirects_text
    finally:
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)
