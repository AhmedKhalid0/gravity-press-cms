"""Static Site Generator (SSG) Compiler, XML Sitemap, and RSS Feed Engine."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import DictLoader, Environment, select_autoescape

from gravitypress.core.cloudflare import CloudflareEdgeManager
from gravitypress.core.parser import MarkdownParser, ParsedDocument


# Built-in Default Fallback Templates
DEFAULT_BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ page_title }}</title>
    <meta name="description" content="{{ page_description }}">
    
    <!-- OpenGraph & Twitter -->
    <meta property="og:title" content="{{ page_title }}">
    <meta property="og:description" content="{{ page_description }}">
    <meta property="og:type" content="{{ og_type|default('website') }}">
    <meta property="og:image" content="{{ og_image|default('https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200') }}">
    <meta name="twitter:card" content="summary_large_image">

    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    
    <style>
        :root {
            --bg-base: #0b0f19;
            --bg-card: #111827;
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #f8fafc;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
            --accent-indigo: #6366f1;
            --accent-cyan: #06b6d4;
            --accent-emerald: #10b981;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: var(--bg-base); color: var(--text-primary); line-height: 1.6; }
        a { color: inherit; text-decoration: none; }
        .container { max-width: 1100px; margin: 0 auto; padding: 0 24px; }
        header { border-bottom: 1px solid var(--border-color); padding: 18px 0; background: rgba(11, 15, 25, 0.85); backdrop-filter: blur(12px); position: sticky; top: 0; z-index: 100; }
        .nav-wrap { display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px; color: var(--text-primary); }
        .logo-gem { background: linear-gradient(135deg, #6366f1, #06b6d4); color: white; padding: 4px 8px; border-radius: 6px; font-size: 14px; font-weight: 900; }
        .nav-links { display: flex; gap: 20px; font-size: 14px; font-weight: 600; color: var(--text-muted); }
        .nav-links a:hover { color: var(--accent-cyan); }
        
        .hero { padding: 60px 0 40px; text-align: center; }
        .hero h1 { font-size: 42px; font-weight: 800; line-height: 1.2; margin-bottom: 16px; background: linear-gradient(135deg, #ffffff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero p { font-size: 18px; color: var(--text-muted); max-width: 680px; margin: 0 auto 30px; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; margin-bottom: 60px; }
        .card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; transition: transform 0.2s, border-color 0.2s; display: flex; flex-direction: column; }
        .card:hover { transform: translateY(-4px); border-color: var(--accent-indigo); }
        .card-img { width: 100%; height: 180px; object-fit: cover; }
        .card-body { padding: 20px; display: flex; flex-direction: column; flex: 1; }
        .card-meta { display: flex; gap: 8px; align-items: center; font-size: 12px; color: var(--accent-cyan); margin-bottom: 8px; font-weight: 600; }
        .card-title { font-size: 18px; font-weight: 700; margin-bottom: 10px; line-height: 1.3; }
        .card-excerpt { font-size: 13px; color: var(--text-muted); margin-bottom: 16px; flex: 1; }
        .card-footer { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--text-dim); border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 12px; }
        
        /* Article Reading View */
        .article-wrap { max-width: 800px; margin: 40px auto 80px; }
        .article-header { margin-bottom: 32px; }
        .article-title { font-size: 38px; font-weight: 800; line-height: 1.25; margin-bottom: 16px; }
        .article-meta-bar { display: flex; gap: 16px; align-items: center; color: var(--text-muted); font-size: 14px; margin-bottom: 24px; }
        .article-banner { width: 100%; height: 380px; object-fit: cover; border-radius: 12px; margin-bottom: 32px; border: 1px solid var(--border-color); }
        
        /* Typography */
        .prose h2 { font-size: 24px; font-weight: 700; margin: 32px 0 16px; color: #fff; }
        .prose h3 { font-size: 20px; font-weight: 600; margin: 24px 0 12px; color: #f1f5f9; }
        .prose p { margin-bottom: 20px; color: #cbd5e1; font-size: 16px; line-height: 1.8; }
        .prose ul, .prose ol { margin: 0 0 20px 24px; color: #cbd5e1; }
        .prose li { margin-bottom: 8px; }
        .prose pre { background: #070a13; border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; overflow-x: auto; margin: 20px 0; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
        .prose code { font-family: 'JetBrains Mono', monospace; background: rgba(255, 255, 255, 0.08); padding: 2px 6px; border-radius: 4px; font-size: 14px; }
        .prose pre code { background: none; padding: 0; }
        .prose blockquote { border-left: 4px solid var(--accent-indigo); padding-left: 16px; margin: 20px 0; font-style: italic; color: #94a3b8; }
        
        footer { border-top: 1px solid var(--border-color); padding: 40px 0; text-align: center; color: var(--text-dim); font-size: 13px; margin-top: auto; }
    </style>
</head>
<body>
    <header>
        <div class="container nav-wrap">
            <a href="/" class="logo">
                <span class="logo-gem">GP</span>
                <span>GravityPress</span>
            </a>
            <nav class="nav-links">
                <a href="/">Articles</a>
                <a href="/feed.xml" target="_blank">RSS Feed</a>
                <a href="/admin/" target="_blank" style="color: var(--accent-emerald);">Admin Studio ⚡</a>
            </nav>
        </div>
    </header>

    <main class="container">
        {% block content %}{% endblock %}
    </main>

    <footer>
        <div class="container">
            <p>Powered by <strong>GravityPress CMS</strong> • Built with FastAPI & Strawberry GraphQL • Deployed globally on Cloudflare Pages</p>
        </div>
    </footer>
</body>
</html>
"""

INDEX_TEMPLATE = """{% extends "base.html" %}

{% block content %}
<section class="hero">
    <h1>High-Performance Headless Content Engine</h1>
    <p>Git-versioned Markdown content, instant GraphQL APIs, and global edge publishing with Cloudflare Pages.</p>
</section>

<section class="grid">
    {% for doc in articles %}
    <article class="card">
        <a href="/articles/{{ doc.metadata.slug }}/">
            <img src="{{ doc.metadata.featured_image }}" alt="{{ doc.metadata.title }}" class="card-img">
        </a>
        <div class="card-body">
            <div class="card-meta">
                <span>{{ doc.metadata.category }}</span>
                <span>•</span>
                <span>{{ doc.reading_time_minutes }} min read</span>
            </div>
            <h2 class="card-title">
                <a href="/articles/{{ doc.metadata.slug }}/">{{ doc.metadata.title }}</a>
            </h2>
            <p class="card-excerpt">{{ doc.metadata.excerpt }}</p>
            <div class="card-footer">
                <span>By {{ doc.metadata.author.name }}</span>
                <span>{{ doc.metadata.date }}</span>
            </div>
        </div>
    </article>
    {% endfor %}
</section>
{% endblock %}
"""

ARTICLE_TEMPLATE = """{% extends "base.html" %}

{% block content %}
<article class="article-wrap">
    <div class="article-header">
        <div class="card-meta" style="font-size: 14px; margin-bottom: 12px;">
            <span>{{ doc.metadata.category }}</span>
            <span>•</span>
            <span>{{ doc.reading_time_minutes }} min read</span>
            <span>•</span>
            <span>{{ doc.word_count }} words</span>
        </div>
        <h1 class="article-title">{{ doc.metadata.title }}</h1>
        <div class="article-meta-bar">
            <span>By <strong>{{ doc.metadata.author.name }}</strong> ({{ doc.metadata.author.role }})</span>
            <span>Published on {{ doc.metadata.date }}</span>
        </div>
    </div>

    {% if doc.metadata.featured_image %}
    <img src="{{ doc.metadata.featured_image }}" alt="{{ doc.metadata.title }}" class="article-banner">
    {% endif %}

    <div class="prose">
        {{ doc.html_content|safe }}
    </div>
</article>
{% endblock %}
"""


class StaticSiteGenerator:
    """Compiles Markdown documents into static HTML, sitemaps, RSS feeds, and Cloudflare manifests."""

    def __init__(self, content_dir: str | Path = "content", output_dir: str | Path = "dist"):
        self.content_dir = Path(content_dir)
        self.output_dir = Path(output_dir)
        self.parser = MarkdownParser()
        self.cf_manager = CloudflareEdgeManager()

    def load_all_documents(self) -> List[ParsedDocument]:
        """Loads and parses all markdown files in the content directory."""
        docs = []
        if not self.content_dir.exists():
            return docs

        for root, _, files in os.walk(self.content_dir):
            for file in files:
                if file.endswith((".md", ".mdx")):
                    fpath = Path(root) / file
                    try:
                        doc = self.parser.parse_file(fpath)
                        if doc.metadata.status == "PUBLISHED":
                            docs.append(doc)
                    except Exception as e:
                        print(f"[Warning] Failed to parse {fpath}: {e}")

        # Sort by latest date descending
        docs.sort(key=lambda d: d.metadata.date, reverse=True)
        return docs

    def build(self, site_url: str = "https://gravity-press-site.pages.dev") -> Dict[str, Any]:
        """Runs the complete SSG build pipeline."""
        start_time = datetime.now()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        docs = self.load_all_documents()

        # Initialize Jinja Environment with DictLoader
        env = Environment(
            loader=DictLoader({
                "base.html": DEFAULT_BASE_TEMPLATE,
                "index.html": INDEX_TEMPLATE,
                "article.html": ARTICLE_TEMPLATE,
            }),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # 1. Render Index Page
        index_tmpl = env.get_template("index.html")
        rendered_index = index_tmpl.render(
            page_title="GravityPress CMS | High-Performance Content Engine",
            page_description="Git-versioned Markdown content and instant GraphQL APIs with Cloudflare Edge deployment.",
            articles=docs,
        )
        (self.output_dir / "index.html").write_text(rendered_index, encoding="utf-8")

        # 2. Render Individual Article Pages
        article_tmpl = env.get_template("article.html")
        for doc in docs:
            art_dir = self.output_dir / "articles" / doc.metadata.slug
            art_dir.mkdir(parents=True, exist_ok=True)

            rendered_art = article_tmpl.render(
                page_title=f"{doc.metadata.title} | GravityPress",
                page_description=doc.metadata.excerpt,
                doc=doc,
                og_type="article",
                og_image=doc.metadata.featured_image,
            )
            (art_dir / "index.html").write_text(rendered_art, encoding="utf-8")

        # 3. Generate XML Sitemap
        self._generate_sitemap(docs, site_url)

        # 4. Generate RSS Feed
        self._generate_rss_feed(docs, site_url)

        # 5. Generate Cloudflare Edge Manifests (_headers, _redirects)
        self.cf_manager.generate_edge_manifests(self.output_dir)

        duration = (datetime.now() - start_time).total_seconds()

        return {
            "status": "success",
            "articles_count": len(docs),
            "output_directory": str(self.output_dir.resolve()),
            "build_duration_seconds": round(duration, 3),
        }

    def _generate_sitemap(self, docs: List[ParsedDocument], site_url: str) -> None:
        """Generates Google-compliant XML Sitemap."""
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            f'  <url><loc>{site_url}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>',
        ]

        for doc in docs:
            loc = f"{site_url}/articles/{doc.metadata.slug}/"
            xml_lines.append(
                f'  <url><loc>{loc}</loc><lastmod>{doc.metadata.date}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>'
            )

        xml_lines.append("</urlset>")
        (self.output_dir / "sitemap.xml").write_text("\n".join(xml_lines), encoding="utf-8")

    def _generate_rss_feed(self, docs: List[ParsedDocument], site_url: str) -> None:
        """Generates RSS 2.0 Feed."""
        pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
            '<channel>',
            '  <title>GravityPress CMS Feed</title>',
            f'  <link>{site_url}/</link>',
            '  <description>High-Performance Headless Content Engine Articles & Guides</description>',
            '  <language>en-us</language>',
            f'  <lastBuildDate>{pub_date}</lastBuildDate>',
        ]

        for doc in docs:
            link = f"{site_url}/articles/{doc.metadata.slug}/"
            xml_lines.extend([
                '  <item>',
                f'    <title><![CDATA[{doc.metadata.title}]]></title>',
                f'    <link>{link}</link>',
                f'    <guid>{link}</guid>',
                f'    <description><![CDATA[{doc.metadata.excerpt}]]></description>',
                f'    <pubDate>{doc.metadata.date}</pubDate>',
                f'    <category>{doc.metadata.category}</category>',
                '  </item>',
            ])

        xml_lines.extend(["</channel>", "</rss>"])
        (self.output_dir / "feed.xml").write_text("\n".join(xml_lines), encoding="utf-8")
