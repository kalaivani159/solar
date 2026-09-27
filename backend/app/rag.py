import math
import os
import re
from typing import Any, Dict, List

from .config import KNOWLEDGE_DIR

STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "in", "for", "to", "and", "or", "on", "by",
    "what", "how", "many", "does", "do", "this", "that", "with", "from", "it", "its",
    "be", "can", "which", "why", "show", "tell", "me", "about", "total", "at", "as",
    "if", "then", "when", "their", "there", "we", "you", "our",
}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9₹]+", text.lower())


class KnowledgeBase:
    def __init__(self, directory: str = KNOWLEDGE_DIR):
        self.directory = directory
        self.chunks: List[Dict[str, Any]] = []
        self.documents: List[str] = []
        self._load()

    def _load(self):
        if not os.path.isdir(self.directory):
            return
        for fname in sorted(os.listdir(self.directory)):
            if not fname.endswith(".md"):
                continue
            path = os.path.join(self.directory, fname)
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            self.documents.append(fname)
            title = content.splitlines()[0].lstrip("# ").strip() if content else fname
            current_heading, buffer = title, []
            for line in content.splitlines():
                if line.startswith("#"):
                    if buffer:
                        self.chunks.append(
                            {
                                "source": fname,
                                "title": title,
                                "heading": current_heading,
                                "text": "\n".join(buffer).strip(),
                            }
                        )
                        buffer = []
                    current_heading = line.lstrip("# ").strip()
                else:
                    buffer.append(line)
            if buffer:
                self.chunks.append(
                    {
                        "source": fname,
                        "title": title,
                        "heading": current_heading,
                        "text": "\n".join(buffer).strip(),
                    }
                )
        for chunk in self.chunks:
            chunk["tokens"] = set(_tokenize(chunk["text"] + " " + chunk["heading"]))

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        terms = [t for t in _tokenize(query) if t not in STOPWORDS and len(t) > 2]
        if not terms:
            return []
        n = max(1, len(self.chunks))
        df: Dict[str, int] = {}
        for chunk in self.chunks:
            for term in set(terms):
                if any(term in tok for tok in chunk["tokens"]):
                    df[term] = df.get(term, 0) + 1
        idf = {
            term: math.log((n + 1) / (df.get(term, 0) + 0.5)) for term in terms
        }
        total_idf = sum(idf.values()) or 1.0

        scored = []
        for chunk in self.chunks:
            tokens = chunk["tokens"]
            matched = [
                t for t in terms if any(t in tok for tok in tokens)
            ]
            if not matched:
                continue
            coverage = sum(idf[t] for t in matched) / total_idf
            density = min(1.0, len(matched) / max(3, len(chunk["text"]) / 500))
            heading_terms = set(_tokenize(chunk["heading"] + " " + chunk["title"]))
            heading_bonus = 0.18 * sum(
                1 for t in terms if t in heading_terms
            ) / max(1, len(terms))
            file_terms = set(_tokenize(chunk["source"].replace(".md", "").replace("_", " ")))
            file_bonus = 0.12 * sum(1 for t in terms if t in file_terms) / max(1, len(terms))
            score = coverage * 0.6 + density * 0.2 + heading_bonus + file_bonus
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, chunk in scored[:top_k]:
            out.append(
                {
                    "source": chunk["source"],
                    "heading": chunk["heading"],
                    "text": chunk["text"][:1200],
                    "relevance": round(score, 3),
                }
            )
        return out

    def list_documents(self) -> List[Dict[str, Any]]:
        docs = []
        for fname in self.documents:
            titles = {c["title"] for c in self.chunks if c["source"] == fname}
            docs.append(
                {
                    "filename": fname,
                    "title": next(iter(titles), fname),
                    "chunks": sum(1 for c in self.chunks if c["source"] == fname),
                }
            )
        return docs


kb = KnowledgeBase()
