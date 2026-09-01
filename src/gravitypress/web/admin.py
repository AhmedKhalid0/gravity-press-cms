"""Web Admin Dashboard, Live Markdown Editor, and Cloudflare Trigger UI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader

from gravitypress.core.cloudflare import CloudflareEdgeManager
from gravitypress.core.git_sync import GitSyncEngine
from gravitypress.core.parser import MarkdownParser
from gravitypress.core.seo import SEOAnalyzer
from gravitypress.core.ssg import StaticSiteGenerator

admin_router = APIRouter(tags=["Admin UI"])

TEMPLATE_DIR = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

parser = MarkdownParser()
git_engine = GitSyncEngine()
cf_manager = CloudflareEdgeManager()
ssg = StaticSiteGenerator()


@admin_router.get("/", response_class=HTMLResponse)
@admin_router.get("/admin/", response_class=HTMLResponse)
async def admin_dashboard_view(request: Request):
    """Renders Admin Dashboard with content metrics, Git history, and Cloudflare status."""
    docs = ssg.load_all_documents()
    recent_commits = git_engine.get_recent_commits(max_count=8)

    total_words = sum(d.word_count for d in docs)
    categories = sorted({d.metadata.category for d in docs})

    template = env.get_template("dashboard.html")
    return template.render(
        request=request,
        articles=docs,
        total_articles=len(docs),
        total_words=total_words,
        categories=categories,
        recent_commits=recent_commits,
        page_title="Admin Control Center | GravityPress CMS",
    )


@admin_router.get("/admin/editor/", response_class=HTMLResponse)
@admin_router.get("/admin/editor/{slug}", response_class=HTMLResponse)
async def admin_editor_view(request: Request, slug: Optional[str] = None):
    """Renders Split-Screen Markdown / MDX Visual Studio."""
    doc = None
    if slug:
        docs = ssg.load_all_documents()
        doc = next((d for d in docs if d.metadata.slug == slug), None)

    initial_markdown = ""
    if doc:
        initial_markdown = doc.raw_markdown
    else:
        initial_markdown = """---
title: "Building Resilient Cloud-Native Edge APIs"
slug: "building-resilient-edge-apis"
category: "Engineering"
status: "PUBLISHED"
featured_image: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200"
excerpt: "A comprehensive guide to building zero-latency edge applications with Cloudflare Pages."
author:
  name: "Ahmed Khaled"
  role: "Lead Systems Architect"
tags:
  - Cloudflare
  - Edge
  - Python
---

## Executive Summary

Edge computing relocates logic closer to the user, drastically slashing round-trip time (RTT).

### Key Architectural Pillars

* **Micro-Caching**: Invalidate cache via Cloudflare API.
* **Declarative Schemas**: Type-safe GraphQL contracts.
* **Git Versioning**: Every change tracked atomically.

```python
async def query_edge():
    return {"status": "fast", "latency_ms": 2.4}
```
"""

    template = env.get_template("editor.html")
    return template.render(
        request=request,
        doc=doc,
        initial_markdown=initial_markdown,
        page_title="Markdown Visual Studio | GravityPress CMS",
    )


@admin_router.post("/admin/editor/save")
async def admin_save_article_form(
    title: str = Form(...),
    slug: str = Form(...),
    category: str = Form("General"),
    tags: str = Form(""),
    status: str = Form("PUBLISHED"),
    excerpt: str = Form(""),
    featured_image: str = Form(""),
    markdown_content: str = Form(...),
    deploy_cloudflare: Optional[str] = Form(None),
):
    """Processes editor form submission, updates Git, and optionally triggers Cloudflare."""
    content_dir = Path("content/articles")
    content_dir.mkdir(parents=True, exist_ok=True)
    target_file = content_dir / f"{slug}.md"

    # Extract tags list
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    tags_yaml = "\n".join([f"  - {t}" for t in tag_list]) if tag_list else "  - General"
    img = featured_image or "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200"

    full_text = f"""---
title: "{title}"
slug: "{slug}"
category: "{category}"
status: "{status}"
featured_image: "{img}"
excerpt: "{excerpt or title}"
author:
  name: "Ahmed Khaled"
  role: "Lead Systems Architect"
tags:
{tags_yaml}
---

{markdown_content}
"""
    is_new = not target_file.exists()
    target_file.write_text(full_text, encoding="utf-8")

    # Commit to Git
    action_verb = "created" if is_new else "updated"
    git_engine.commit_file(
        target_file,
        f"cms: {action_verb} article '{title}'",
        author_name="Ahmed Khaled",
    )

    # If Cloudflare deployment requested
    if deploy_cloudflare:
        ssg.build()
        await cf_manager.purge_zone_cache()

    return RedirectResponse(url=f"/admin/editor/{slug}?saved=1", status_code=303)
