"""Shared bounded BM25 retrieval, without lifecycle or trust bonuses."""

from __future__ import annotations

import math
import re
from collections import Counter

SCORER_VERSION = "bm25-en-zh-v1"
REUSE_THRESHOLD = 0.65
CONTEXT_CHARS = 500
CONTEXT_WEIGHT = 0.15
STOPWORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "from",
        "by",
        "is",
        "are",
        "be",
        "this",
        "that",
        "it",
        "as",
        "at",
        "use",
        "when",
        "needs",
        "need",
        "please",
        "help",
        "task",
        "specific",
        "agent",
        "的",
        "了",
        "和",
        "是",
        "在",
        "与",
        "或",
        "请",
        "帮",
        "我",
        "将",
        "把",
        "对",
        "为",
        "以及",
        "一个",
        "进行",
        "需要",
        "使用",
    ]
)


def stem(word: str) -> str:
    if len(word) > 5 and word.endswith("ies"):
        return word[:-3] + "y"
    for suffix in ("ing", "ed", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            base = word[: -len(suffix)]
            if suffix in {"ing", "ed"} and len(base) > 2 and base[-1] == base[-2]:
                base = base[:-1]
            return base
    return word


def tokenize(text: str) -> list[str]:
    tokens = []
    for part in re.findall(r"[a-z0-9]+|[\u3400-\u9fff]+", text.lower()):
        if part in STOPWORDS:
            continue
        if part.isascii():
            if len(part) > 1:
                tokens.append(stem(part))
        else:
            for chunk in re.split("[的了和是在与或请帮我将把对为]", part):
                tokens.extend(
                    chunk[i : i + 2]
                    for i in range(len(chunk) - 1)
                    if chunk[i : i + 2] not in STOPWORDS
                )
    return tokens


def entry_text(entry: dict) -> str:
    fields = [str(entry.get(key) or "") for key in ("name", "title", "description")]
    for key in ("tags", "repo_tags"):
        tags = entry.get(key, [])
        fields.append(" ".join(map(str, tags)) if isinstance(tags, list) else str(tags))
    return " ".join(fields)


class BM25:
    """BM25 (k1=1.2, b=.25), divided by query self-match, clipped to [0, 1]."""

    def __init__(self, entries: list[dict]):
        self.documents = [Counter(tokenize(entry_text(entry))) for entry in entries]
        self.average_length = (
            sum(sum(d.values()) for d in self.documents) / max(len(entries), 1) or 1
        )
        frequencies = Counter(term for document in self.documents for term in document)
        self.idf = {
            term: math.log(1 + (len(entries) - count + 0.5) / (count + 0.5))
            for term, count in frequencies.items()
        }
        # Unseen terms receive the rarest observed IDF; in a one-document corpus
        # they must not outweigh every matching term several times over.
        self.missing_idf = max(self.idf.values(), default=math.log(2))

    def raw(self, document: Counter, query: set[str]) -> float:
        norm = 1.2 * (0.75 + 0.25 * sum(document.values()) / self.average_length)
        return sum(
            self.idf.get(term, self.missing_idf) * document[term] * 2.2 / (document[term] + norm)
            for term in query
            if document[term]
        )

    def similarity(self, document: Counter, text: str) -> float:
        query = set(tokenize(text))
        if not query:
            return 0.0
        denominator = self.raw(Counter(query), query)
        return min(1.0, self.raw(document, query) / denominator) if denominator else 0.0

    def score(self, index: int, intent: str, context: str = "") -> float:
        document = self.documents[index]
        primary = self.similarity(document, intent)
        if not primary:
            return 0.0
        if not tokenize(context[:CONTEXT_CHARS]):
            return primary
        return (primary + CONTEXT_WEIGHT * self.similarity(document, context[:CONTEXT_CHARS])) / (
            1 + CONTEXT_WEIGHT
        )
