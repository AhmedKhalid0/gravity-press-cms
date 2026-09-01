"""FastAPI REST API Endpoints for Headless Content Delivery."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from gravitypress.core.cloudflare import CloudflareEdgeManager
from gravitypress.core.git_sync import GitSyncEngine
from gravitypress.core.parser import AuthorInfo, MarkdownParser, ParsedDocument
from gravitypress.core.search import BM25SearchEngine
from gravitypress.core.seo import SEOAnalyzer
from gravitypress.core.ssg import StaticSiteGenerator

router = APIRouter(prefix="/api/v1", tags=["Content Delivery"])

parser = MarkdownParser()
git_engine = GitSyncEngine()
cf_manager = CloudflareEdgeManager()
search_engine = BM25SearchEngine()


class ArticleCreatePayload(BaseModel):
    title: str = Field(..., json_schema_extra={"example": "Architecting Cloud-Native Microservices with Python 3.14"})
    slug: Optional[str] = Field(None, json_schema_extra={"example": "cloud-native-microservices-python-314"})
    category: str = Field("Engineering", json_schema_extra={"example": "Engineering"})
    tags: List[str] = Field(default_factory=list, json_schema_extra={"example": ["Python", "FastAPI", "Cloudflare"]})
    excerpt: Optional[str] = Field(None, json_schema_extra={"example": "An architectural guide to zero-latency microservices."})
    content_markdown: str = Field(..., json_schema_extra={"example": "## Architecture Overview\n\nThis is the markdown body."})
    featured_image: Optional[str] = Field(None, json_schema_extra={"example": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200"})
    status: str = Field("PUBLISHED", json_schema_extra={"example": "PUBLISHED"})
    author_name: Optional[str] = Field("Ahmed Khaled", json_schema_extra={"example": "Ahmed Khaled"})
    commit_to_git: bool = Field(True, json_schema_extra={"example": True})


def get_all_parsed_articles() -> List[ParsedDocument]:
    """Helper to parse all articles from content directory and update search index."""
    ssg = StaticSiteGenerator()
    docs = ssg.load_all_documents()
    search_engine.build_index(docs)
    return docs


@router.get("/health/", tags=["Telemetry"])
async def health_check():
    """System status and content repository counters."""
    docs = get_all_parsed_articles()
    return {
        "status": "healthy",
        "engine": "GravityPress CMS",
        "version": "1.0.0",
        "articles_count": len(docs),
        "git_initialized": git_engine.is_git_repo(),
    }


@router.get("/content/articles/")
async def list_articles(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    author: Optional[str] = None,
    status_filter: Optional[str] = Query("PUBLISHED", alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Retrieves paginated articles with faceted filtering."""
    docs = get_all_parsed_articles()

    if category:
        docs = [d for d in docs if d.metadata.category.lower() == category.lower()]
    if tag:
        docs = [d for d in docs if any(t.lower() == tag.lower() for t in d.metadata.tags)]
    if author:
        docs = [d for d in docs if author.lower() in d.metadata.author.name.lower()]
    if status_filter:
        docs = [d for d in docs if d.metadata.status.upper() == status_filter.upper()]

    total = len(docs)
    paginated = docs[offset : offset + limit]

    results = []
    for d in paginated:
        results.append({
            "title": d.metadata.title,
            "slug": d.metadata.slug,
            "date": d.metadata.date,
            "category": d.metadata.category,
            "tags": d.metadata.tags,
            "excerpt": d.metadata.excerpt,
            "featured_image": d.metadata.featured_image,
            "reading_time_minutes": d.reading_time_minutes,
            "word_count": d.word_count,
            "author": {
                "name": d.metadata.author.name,
                "role": d.metadata.author.role,
                "avatar": d.metadata.author.avatar,
            },
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "articles": results,
    }


@router.get("/content/articles/{slug}")
async def get_article_detail(slug: str):
    """Retrieves full article details including rendered HTML and Table of Contents."""
    docs = get_all_parsed_articles()
    match = next((d for d in docs if d.metadata.slug == slug), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Article with slug '{slug}' not found.")

    # Get Git history if available
    git_history = []
    if match.file_path:
        history_records = git_engine.get_file_history(match.file_path, max_count=5)
        git_history = [{"hash": h.hash, "author": h.author, "date": h.date, "message": h.message} for h in history_records]

    # Calculate live SEO score
    seo_res = SEOAnalyzer.analyze(
        title=match.metadata.title,
        description=match.metadata.excerpt,
        markdown_body=match.raw_markdown,
        featured_image=match.metadata.featured_image,
        author_name=match.metadata.author.name,
    )

    return {
        "metadata": match.metadata.to_dict(),
        "html_content": match.html_content,
        "raw_markdown": match.raw_markdown,
        "toc_html": match.toc_html,
        "toc_tokens": match.toc_tokens,
        "reading_time_minutes": match.reading_time_minutes,
        "word_count": match.word_count,
        "seo_score": seo_res.score,
        "seo_grade": seo_res.grade,
        "git_revisions": git_history,
    }


@router.post("/content/articles/", status_code=status.HTTP_201_CREATED)
async def create_or_update_article(payload: ArticleCreatePayload):
    """Creates or updates a Markdown article and commits to Git version control."""
    slug = payload.slug or parser._slugify(payload.title)
    content_dir = Path("content/articles")
    content_dir.mkdir(parents=True, exist_ok=True)
    target_file = content_dir / f"{slug}.md"

    # Construct YAML frontmatter
    tags_yaml = "\n".join([f"  - {t}" for t in payload.tags]) if payload.tags else "  - General"
    featured_img = payload.featured_image or "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200"

    file_content = f"""---
title: "{payload.title}"
slug: "{slug}"
category: "{payload.category}"
status: "{payload.status}"
featured_image: "{featured_img}"
excerpt: "{payload.excerpt or payload.title}"
author:
  name: "{payload.author_name or 'Ahmed Khaled'}"
  role: "Lead Systems Architect"
  avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"
tags:
{tags_yaml}
---

{payload.content_markdown}
"""
    is_new = not target_file.exists()
    target_file.write_text(file_content, encoding="utf-8")

    commit_hash = None
    if payload.commit_to_git:
        action_verb = "create" if is_new else "update"
        commit_hash = git_engine.commit_file(
            target_file,
            f"cms: {action_verb} article '{payload.title}'",
            author_name=payload.author_name or "GravityPress CMS",
        )

    return {
        "status": "success",
        "slug": slug,
        "file_path": str(target_file),
        "is_new": is_new,
        "git_commit_hash": commit_hash,
    }


@router.get("/content/search")
async def search_content(q: str = Query(..., min_length=1), limit: int = 10):
    """Performs instant in-memory BM25 full-text search across all articles."""
    get_all_parsed_articles()  # Ensures index is warm
    results = search_engine.search(q, limit=limit)

    return {
        "query": q,
        "count": len(results),
        "results": [
            {
                "title": r.document.metadata.title,
                "slug": r.document.metadata.slug,
                "category": r.document.metadata.category,
                "score": r.score,
                "snippet": r.snippet,
                "matched_terms": r.matched_terms,
            }
            for r in results
        ],
    }


@router.post("/deploy/cloudflare", tags=["Cloudflare Edge"])
async def deploy_to_cloudflare():
    """Builds static site and triggers Cloudflare Pages Edge Deployment & Cache Purge."""
    ssg = StaticSiteGenerator()
    build_result = ssg.build()

    # Trigger purge or deploy hook if configured
    purge_result = await cf_manager.purge_zone_cache()
    hook_result = await cf_manager.trigger_deploy_hook()

    return {
        "status": "success",
        "ssg_build": build_result,
        "cloudflare_cache_purge": purge_result,
        "cloudflare_deploy_hook": hook_result,
    }
