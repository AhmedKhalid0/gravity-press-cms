"""SEO, Readability, and OpenGraph Meta Analysis Engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SEOAnalysisResult:
    score: int  # 0 to 100
    grade: str  # Excellent, Good, Needs Improvement, Poor
    title_score: int
    description_score: int
    content_score: int
    readability_score: int
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    open_graph_tags: Dict[str, str] = field(default_factory=dict)


class SEOAnalyzer:
    """Calculates SEO health score, readability grade, and meta tags for articles."""

    @classmethod
    def analyze(
        cls,
        title: str,
        description: str,
        markdown_body: str,
        canonical_url: str = "",
        featured_image: str = "",
        author_name: str = "",
    ) -> SEOAnalysisResult:
        issues = []
        recommendations = []

        # 1. Title Analysis (40 - 60 chars is ideal)
        title_len = len(title.strip())
        if 40 <= title_len <= 65:
            title_score = 100
        elif 25 <= title_len < 40:
            title_score = 80
            recommendations.append(f"Title length is {title_len} chars. Expanding to 45-60 chars improves search click-through rate.")
        elif title_len > 65:
            title_score = 70
            issues.append(f"Title is {title_len} chars long and may be truncated on Google search results (limit: ~60 chars).")
        else:
            title_score = 50
            issues.append("Title is too short. Provide a more descriptive and engaging headline.")

        # 2. Description Analysis (120 - 160 chars is ideal)
        desc_len = len(description.strip())
        if 120 <= desc_len <= 165:
            desc_score = 100
        elif 80 <= desc_len < 120:
            desc_score = 85
            recommendations.append("Meta description is slightly short. Aim for 130-155 characters for optimal snippet coverage.")
        elif desc_len > 165:
            desc_score = 75
            issues.append("Meta description exceeds 160 characters and will be clipped by search engines.")
        elif desc_len > 0:
            desc_score = 60
            issues.append("Meta description is under 80 characters. Elaborate on the article's core value.")
        else:
            desc_score = 20
            issues.append("Meta description is missing.")

        # 3. Content Body Analysis
        words = re.findall(r"\b\w+\b", markdown_body)
        word_count = len(words)
        headings = re.findall(r"^#{1,3}\s+(.+)$", markdown_body, re.MULTILINE)

        content_score = 100
        if word_count < 300:
            content_score = 50
            issues.append(f"Content is only {word_count} words. Deep technical articles usually perform best with 800+ words.")
        elif word_count < 600:
            content_score = 80
            recommendations.append("Consider adding code samples, architectural diagrams, or case studies to increase depth.")

        if len(headings) < 2:
            content_score = max(40, content_score - 20)
            issues.append("Document lacks sub-headings (H2/H3). Break down content into structured sections.")

        # 4. Readability Score
        sentences = max(1, len(re.split(r"[.!?]+", markdown_body)))
        avg_words_per_sentence = word_count / sentences

        if avg_words_per_sentence <= 18:
            readability_score = 95
        elif avg_words_per_sentence <= 25:
            readability_score = 80
        else:
            readability_score = 65
            recommendations.append("Average sentence length is high. Consider breaking complex sentences for improved readability.")

        # Composite Score (Weighted)
        composite = int(
            (title_score * 0.25)
            + (desc_score * 0.25)
            + (content_score * 0.35)
            + (readability_score * 0.15)
        )
        composite = max(10, min(100, composite))

        if composite >= 90:
            grade = "Excellent"
        elif composite >= 75:
            grade = "Good"
        elif composite >= 60:
            grade = "Needs Improvement"
        else:
            grade = "Poor"

        # Generate OpenGraph and Twitter tags
        og_tags = {
            "og:title": title,
            "og:description": description,
            "og:type": "article",
            "og:url": canonical_url,
            "og:image": featured_image,
            "twitter:card": "summary_large_image",
            "twitter:title": title,
            "twitter:description": description,
            "twitter:image": featured_image,
            "author": author_name,
        }

        return SEOAnalysisResult(
            score=composite,
            grade=grade,
            title_score=title_score,
            description_score=desc_score,
            content_score=content_score,
            readability_score=readability_score,
            issues=issues,
            recommendations=recommendations,
            open_graph_tags=og_tags,
        )
