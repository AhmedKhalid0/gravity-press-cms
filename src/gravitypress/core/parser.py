"""Markdown AST Parser and YAML Frontmatter Extractor with Code Highlighting and TOC generation."""

from __future__ import annotations

import math
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import markdown
import yaml


@dataclass
class AuthorInfo:
    name: str = "Ahmed Khaled"
    role: str = "Lead Systems Architect"
    avatar: str = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"
    email: str = "contact@ahmedalgendy.com"


@dataclass
class ArticleMetadata:
    title: str
    slug: str
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    author: AuthorInfo = field(default_factory=AuthorInfo)
    category: str = "General"
    tags: List[str] = field(default_factory=list)
    excerpt: str = ""
    status: str = "PUBLISHED"  # DRAFT or PUBLISHED
    featured_image: str = "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200"
    seo_title: str = ""
    seo_description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


@dataclass
class ParsedDocument:
    metadata: ArticleMetadata
    raw_markdown: str
    html_content: str
    toc_html: str
    toc_tokens: List[Dict[str, Any]]
    word_count: int
    reading_time_minutes: int
    file_path: Optional[str] = None


class MarkdownParser:
    """Enterprise Markdown AST parser with Frontmatter extraction and Pygments syntax highlighting."""

    FRONTMATTER_REGEX = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def __init__(self):
        self.md = markdown.Markdown(
            extensions=[
                "extra",
                "fenced_code",
                "codehilite",
                "tables",
                "toc",
                "attr_list",
                "sane_lists",
            ],
            extension_configs={
                "codehilite": {
                    "css_class": "highlight",
                    "linenums": False,
                    "guess_lang": True,
                },
                "toc": {
                    "permalink": False,
                },
            },
        )

    def parse_text(self, text: str, file_path: Optional[str] = None) -> ParsedDocument:
        """Parses raw markdown string with YAML frontmatter into structured AST and HTML."""
        frontmatter_data = {}
        body_text = text

        match = self.FRONTMATTER_REGEX.match(text)
        if match:
            raw_fm = match.group(1)
            try:
                frontmatter_data = yaml.safe_load(raw_fm) or {}
            except Exception:
                frontmatter_data = {}
            body_text = text[match.end() :]

        # Extract or fallback title and slug
        title = frontmatter_data.get("title", "Untitled Document")
        slug = frontmatter_data.get("slug")
        if not slug:
            slug = self._slugify(title)

        author_data = frontmatter_data.get("author", {})
        if isinstance(author_data, str):
            author = AuthorInfo(name=author_data)
        elif isinstance(author_data, dict):
            author = AuthorInfo(
                name=author_data.get("name", "Ahmed Khaled"),
                role=author_data.get("role", "Lead Systems Architect"),
                avatar=author_data.get("avatar", "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"),
                email=author_data.get("email", "contact@ahmedalgendy.com"),
            )
        else:
            author = AuthorInfo()

        raw_tags = frontmatter_data.get("tags", [])
        if isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        else:
            tags = list(raw_tags)

        # Word count & Reading time (200 words per min)
        clean_words = re.findall(r"\b\w+\b", body_text)
        word_count = len(clean_words)
        reading_time = max(1, math.ceil(word_count / 200))

        # Excerpt generation if empty
        excerpt = frontmatter_data.get("excerpt", "")
        if not excerpt:
            first_p = re.search(r"^(?!#)(.+)$", body_text, re.MULTILINE)
            if first_p:
                excerpt = first_p.group(1).strip()[:180] + "..."
            else:
                excerpt = f"A deep dive into {title} covering architecture, performance, and best practices."

        metadata = ArticleMetadata(
            title=title,
            slug=slug,
            date=str(frontmatter_data.get("date", datetime.now().strftime("%Y-%m-%d"))),
            author=author,
            category=frontmatter_data.get("category", "Technology"),
            tags=tags,
            excerpt=excerpt,
            status=frontmatter_data.get("status", "PUBLISHED").upper(),
            featured_image=frontmatter_data.get(
                "featured_image",
                "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200",
            ),
            seo_title=frontmatter_data.get("seo_title", title),
            seo_description=frontmatter_data.get("seo_description", excerpt),
        )

        # Reset markdown state and convert
        self.md.reset()
        html_content = self.md.convert(body_text)
        toc_html = getattr(self.md, "toc", "")
        toc_tokens = getattr(self.md, "toc_tokens", [])

        return ParsedDocument(
            metadata=metadata,
            raw_markdown=text,
            html_content=html_content,
            toc_html=toc_html,
            toc_tokens=toc_tokens,
            word_count=word_count,
            reading_time_minutes=reading_time,
            file_path=file_path,
        )

    def parse_file(self, file_path: str | Path) -> ParsedDocument:
        """Reads markdown file from disk and returns parsed document."""
        p = Path(file_path)
        content = p.read_text(encoding="utf-8")
        return self.parse_text(content, file_path=str(p.resolve()))

    @staticmethod
    def _slugify(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text)
        return text.strip("-")
