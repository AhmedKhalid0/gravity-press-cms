"""In-Memory Full-Text Search Engine with BM25 Ranking and Microsecond Queries."""

from __future__ import annotations

import math
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from gravitypress.core.parser import ParsedDocument


@dataclass
class SearchResult:
    document: ParsedDocument
    score: float
    matched_terms: List[str]
    snippet: str


class BM25SearchEngine:
    """High-speed in-memory BM25 full-text indexing engine for markdown documents."""

    STOPWORDS: Set[str] = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
        "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
        "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
        "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
        "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
        "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
        "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
        "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
        "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
        "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
        "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
        "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
        "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
        "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
        "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
        "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
        "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
        "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd",
        "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
    }

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[ParsedDocument] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.doc_term_freqs: List[Counter] = []
        self.inverted_index: Dict[str, Set[int]] = defaultdict(set)
        self.num_docs: int = 0

    def tokenize(self, text: str) -> List[str]:
        """Lowercases, cleans punctuation, and removes common stopwords."""
        words = re.findall(r"\b[a-zA-Z0-9_\-\u0600-\u06FF]+\b", text.lower())
        return [w for w in words if len(w) > 1 and w not in self.STOPWORDS]

    def build_index(self, documents: List[ParsedDocument]) -> None:
        """Indexes an array of parsed documents."""
        self.documents = documents
        self.num_docs = len(documents)
        self.doc_term_freqs = []
        self.doc_lengths = []
        self.inverted_index = defaultdict(set)

        total_length = 0
        for doc_id, doc in enumerate(documents):
            # Combine title (weighted 3x), tags (2x), category (2x), excerpt, and raw body
            weighted_text = (
                f"{doc.metadata.title} {doc.metadata.title} {doc.metadata.title} "
                f"{doc.metadata.category} {doc.metadata.category} "
                f"{' '.join(doc.metadata.tags)} {' '.join(doc.metadata.tags)} "
                f"{doc.metadata.excerpt} {doc.raw_markdown}"
            )
            tokens = self.tokenize(weighted_text)
            self.doc_lengths.append(len(tokens))
            total_length += len(tokens)

            tf = Counter(tokens)
            self.doc_term_freqs.append(tf)

            for term in tf:
                self.inverted_index[term].add(doc_id)

        self.avg_doc_length = total_length / max(1, self.num_docs)

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Searches indexed documents using BM25 scoring."""
        if not self.documents or not query.strip():
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        scores: Dict[int, float] = defaultdict(float)
        matched_terms_map: Dict[int, Set[str]] = defaultdict(set)

        for token in query_tokens:
            matching_docs = self.inverted_index.get(token, set())
            df = len(matching_docs)
            if df == 0:
                continue

            # BM25 Inverse Document Frequency (IDF)
            idf = math.log(1 + (self.num_docs - df + 0.5) / (df + 0.5))

            for doc_id in matching_docs:
                tf = self.doc_term_freqs[doc_id][token]
                doc_len = self.doc_lengths[doc_id]
                
                # BM25 Term Frequency weighting
                denom = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_length))
                score = idf * (tf * (self.k1 + 1)) / denom
                scores[doc_id] += score
                matched_terms_map[doc_id].add(token)

        # Sort by highest score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        results = []
        for doc_id, score in ranked:
            doc = self.documents[doc_id]
            matched = list(matched_terms_map[doc_id])
            snippet = self._generate_snippet(doc.raw_markdown, matched)
            results.append(
                SearchResult(
                    document=doc,
                    score=round(score, 4),
                    matched_terms=matched,
                    snippet=snippet,
                )
            )

        return results

    def _generate_snippet(self, content: str, matched_terms: List[str], max_chars: int = 160) -> str:
        """Extracts text surrounding matched terms."""
        if not matched_terms:
            return content[:max_chars] + "..."

        first_term = matched_terms[0]
        pos = content.lower().find(first_term)
        if pos == -1:
            return content[:max_chars] + "..."

        start = max(0, pos - 40)
        end = min(len(content), pos + max_chars)
        snippet = content[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        return snippet
