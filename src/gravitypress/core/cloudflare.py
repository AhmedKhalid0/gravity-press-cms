"""Cloudflare Pages Integration, Cache Purge, and Edge Headers Generator."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


@dataclass
class CloudflareConfig:
    account_id: Optional[str] = None
    api_token: Optional[str] = None
    project_name: str = "gravity-press-site"
    zone_id: Optional[str] = None
    deploy_hook: Optional[str] = None

    @classmethod
    def from_env(cls) -> CloudflareConfig:
        return cls(
            account_id=os.getenv("CLOUDFLARE_ACCOUNT_ID"),
            api_token=os.getenv("CLOUDFLARE_API_TOKEN"),
            project_name=os.getenv("CLOUDFLARE_PAGES_PROJECT", "gravity-press-site"),
            zone_id=os.getenv("CLOUDFLARE_ZONE_ID"),
            deploy_hook=os.getenv("CLOUDFLARE_DEPLOY_HOOK"),
        )


class CloudflareEdgeManager:
    """Manages Cloudflare Pages deployment manifests, edge headers, and cache purges."""

    def __init__(self, config: Optional[CloudflareConfig] = None):
        self.config = config or CloudflareConfig.from_env()

    def generate_edge_manifests(self, output_dir: str | Path) -> None:
        """Generates Cloudflare Pages _headers and _redirects rules inside the output dist folder."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # 1. Cloudflare _headers file
        headers_content = """# Cloudflare Pages Edge Cache Rules
/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: document-domain=()

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/*.html
  Cache-Control: public, max-age=0, must-revalidate

/feed.xml
  Cache-Control: public, max-age=3600, must-revalidate

/sitemap.xml
  Cache-Control: public, max-age=86400
"""
        (out / "_headers").write_text(headers_content, encoding="utf-8")

        # 2. Cloudflare _redirects file
        redirects_content = """# Cloudflare Pages Redirects
/admin        /admin/           301
/articles     /                 301
"""
        (out / "_redirects").write_text(redirects_content, encoding="utf-8")

    async def purge_zone_cache(self, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Purges Cloudflare Edge Cache via REST API (Entire Zone or specific URLs)."""
        if not self.config.api_token or not self.config.zone_id:
            return {
                "success": False,
                "message": "Cloudflare API token or Zone ID missing from environment.",
                "mock": True,
            }

        url = f"https://api.cloudflare.com/client/v4/zones/{self.config.zone_id}/purge_cache"
        headers = {
            "Authorization": f"Bearer {self.config.api_token}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {"purge_everything": True} if not files else {"files": files}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(url, headers=headers, json=payload)
                data = res.json()
                return {
                    "success": data.get("success", False),
                    "status_code": res.status_code,
                    "response": data,
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                }

    async def trigger_deploy_hook(self) -> Dict[str, Any]:
        """Triggers Cloudflare Pages Deploy Hook to initiate instant edge build."""
        if not self.config.deploy_hook:
            return {
                "success": False,
                "message": "CLOUDFLARE_DEPLOY_HOOK URL not configured in .env",
                "mock": True,
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(self.config.deploy_hook)
                return {
                    "success": res.status_code in [200, 202],
                    "status_code": res.status_code,
                    "message": "Cloudflare Pages deploy hook triggered successfully!",
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    def deploy_via_wrangler(self, output_dir: str | Path = "dist") -> Dict[str, Any]:
        """Executes Wrangler CLI to deploy directory to Cloudflare Pages."""
        out = Path(output_dir).resolve()
        cmd = [
            "npx",
            "wrangler",
            "pages",
            "deploy",
            str(out),
            f"--project-name={self.config.project_name}",
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            return {
                "success": res.returncode == 0,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "returncode": res.returncode,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "npx or wrangler binary not available on system PATH",
            }
