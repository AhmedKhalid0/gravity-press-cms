"""Strawberry GraphQL Schema, Typed Types, and Field Resolvers."""

from __future__ import annotations

from typing import List, Optional

import strawberry

from gravitypress.core.search import BM25SearchEngine
from gravitypress.core.ssg import StaticSiteGenerator

ssg = StaticSiteGenerator()
search_engine = BM25SearchEngine()


@strawberry.type
class AuthorType:
    name: str
    role: str
    avatar: str
    email: str


@strawberry.type
class ArticleType:
    title: str
    slug: str
    date: str
    category: str
    tags: List[str]
    excerpt: str
    featured_image: str
    reading_time_minutes: int
    word_count: int
    html_content: str
    toc_html: str
    author: AuthorType


@strawberry.type
class SearchResultType:
    title: str
    slug: str
    category: str
    score: float
    snippet: str


@strawberry.type
class SiteMetadataType:
    title: str
    tagline: str
    engine: str
    version: str
    total_articles: int
    primary_author: str


def _fetch_all_docs():
    docs = ssg.load_all_documents()
    search_engine.build_index(docs)
    return docs


@strawberry.type
class Query:
    @strawberry.field
    def site_metadata(self) -> SiteMetadataType:
        docs = _fetch_all_docs()
        return SiteMetadataType(
            title="GravityPress CMS",
            tagline="High-Performance Headless Git-Based Content Engine",
            engine="FastAPI + Strawberry GraphQL",
            version="1.0.0",
            total_articles=len(docs),
            primary_author="Ahmed Khaled (Ahmed Algendy)",
        )

    @strawberry.field
    def articles(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ArticleType]:
        docs = _fetch_all_docs()
        if category:
            docs = [d for d in docs if d.metadata.category.lower() == category.lower()]
        if tag:
            docs = [d for d in docs if any(t.lower() == tag.lower() for t in d.metadata.tags)]

        paginated = docs[offset : offset + limit]
        return [
            ArticleType(
                title=d.metadata.title,
                slug=d.metadata.slug,
                date=d.metadata.date,
                category=d.metadata.category,
                tags=d.metadata.tags,
                excerpt=d.metadata.excerpt,
                featured_image=d.metadata.featured_image,
                reading_time_minutes=d.reading_time_minutes,
                word_count=d.word_count,
                html_content=d.html_content,
                toc_html=d.toc_html,
                author=AuthorType(
                    name=d.metadata.author.name,
                    role=d.metadata.author.role,
                    avatar=d.metadata.author.avatar,
                    email=d.metadata.author.email,
                ),
            )
            for d in paginated
        ]

    @strawberry.field
    def article(self, slug: str) -> Optional[ArticleType]:
        docs = _fetch_all_docs()
        match = next((d for d in docs if d.metadata.slug == slug), None)
        if not match:
            return None

        return ArticleType(
            title=match.metadata.title,
            slug=match.metadata.slug,
            date=match.metadata.date,
            category=match.metadata.category,
            tags=match.metadata.tags,
            excerpt=match.metadata.excerpt,
            featured_image=match.metadata.featured_image,
            reading_time_minutes=match.reading_time_minutes,
            word_count=match.word_count,
            html_content=match.html_content,
            toc_html=match.toc_html,
            author=AuthorType(
                name=match.metadata.author.name,
                role=match.metadata.author.role,
                avatar=match.metadata.author.avatar,
                email=match.metadata.author.email,
            ),
        )

    @strawberry.field
    def search_articles(self, query: str, limit: int = 10) -> List[SearchResultType]:
        _fetch_all_docs()
        results = search_engine.search(query, limit=limit)
        return [
            SearchResultType(
                title=r.document.metadata.title,
                slug=r.document.metadata.slug,
                category=r.document.metadata.category,
                score=r.score,
                snippet=r.snippet,
            )
            for r in results
        ]

    @strawberry.field
    def categories(self) -> List[str]:
        docs = _fetch_all_docs()
        cats = sorted({d.metadata.category for d in docs if d.metadata.category})
        return cats

    @strawberry.field
    def tags(self) -> List[str]:
        docs = _fetch_all_docs()
        tags_set = set()
        for d in docs:
            tags_set.update(d.metadata.tags)
        return sorted(tags_set)


schema = strawberry.Schema(query=Query)
