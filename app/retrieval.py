"""Retrieval: splits the knowledge files into sections and finds the most relevant ones
for a question using BM25 (a classic search-engine ranking). No external services needed.

To upgrade later: swap `KnowledgeBase.search` for embeddings + FAISS. Nothing else changes.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are", "was",
    "be", "do", "does", "did", "can", "could", "you", "your", "i", "me", "my", "we", "our",
    "it", "its", "this", "that", "what", "which", "who", "how", "when", "where", "why", "about",
    "tell", "please", "have", "has", "any", "at", "by", "from", "as", "he", "his", "him", "they",
    "there", "here", "so", "if", "not", "no", "yes", "hi", "hello", "hey", "will", "would", "much",
}

# words visitors use that map to words in the knowledge files
SYNONYMS = {
    "price": ["prices", "pricing", "cost", "quote"], "cost": ["price", "pricing"],
    "hire": ["hire", "freelance", "contact", "quote"], "phone": ["whatsapp", "contact"],
    "call": ["whatsapp", "phone", "contact"], "email": ["contact", "email"],
    "shop": ["virtual", "room", "beddings", "business"], "linen": ["virtual", "room", "beddings", "products"],
    "bedding": ["beddings", "linen", "bedsheets"], "sheet": ["bedsheets"], "sheets": ["bedsheets"],
    "blanket": ["duvets"], "duvet": ["duvets"], "pillow": ["pillows"], "towel": ["towels"],
    "mattress": ["mattress", "toppers", "protectors"], "deliver": ["delivery"], "deliveries": ["delivery"],
    "order": ["order", "whatsapp"], "buy": ["order", "products"], "location": ["mbarara", "mile"],
    "where": ["location"], "skill": ["skills", "stack"], "stack": ["skills", "stack"],
    "language": ["javascript", "python", "stack"], "languages": ["javascript", "python", "stack"],
    "security": ["cyber", "security", "ethical", "hacking"], "hacking": ["ethical", "hacking", "penetration"],
    "forensic": ["forensics"], "app": ["apps", "mobile", "flutter"], 
    "school": ["university", "must", "student"], "study": ["university", "student", "software", "engineering"],
    "studying": ["university", "student", "software", "engineering"], "degree": ["bsc", "university"],
    "who": ["who"], "available": ["availability", "freelance"], "freelance": ["availability", "freelance"],
    "website": ["web", "websites", "services"], "websites": ["web", "services"],
    "experience": ["experience"], "work": ["experience", "projects"], "project": ["projects"],
    "github": ["github", "code"], "code": ["github", "code"], "design": ["graphic", "design"],
    "chatbot": ["rag", "chatbots"], "ai": ["ai", "rag"],
}


def _stem(word: str) -> str:
    for suffix in ("ing", "ies", "es", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


PHRASES = {"how much": "price", "how many": "stock", "get in touch": "contact", "reach him": "contact",
           "who is": "student university founder engineering", "about him": "student university founder",
           "for my business": "services web apps", "for my company": "services"}


def tokenize(text: str, expand: bool = False) -> list[str]:
    low = text.lower()
    if expand:
        low += " " + " ".join(v for k, v in PHRASES.items() if k in low)
    words = [w for w in re.findall(r"[a-z0-9+#.]+", low) if w not in STOPWORDS]
    words = [w.strip(".") for w in words if w.strip(".")]
    if expand:
        extra = [s for w in words for s in SYNONYMS.get(w, SYNONYMS.get(_stem(w), []))]
        words += extra
    return [_stem(w) for w in words]


@dataclass
class Chunk:
    source: str   # file name
    title: str    # "File title > Section heading"
    text: str


def load_chunks(folder: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(folder.glob("*.md")):
        doc_title, section, lines = path.stem, None, []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                doc_title = line[2:].strip()
            elif line.startswith("## "):
                if section and "".join(lines).strip():
                    chunks.append(Chunk(path.name, f"{doc_title} > {section}", "\n".join(lines).strip()))
                section, lines = line[3:].strip(), []
            else:
                lines.append(line)
        if section and "".join(lines).strip():
            chunks.append(Chunk(path.name, f"{doc_title} > {section}", "\n".join(lines).strip()))
        elif not section and "".join(lines).strip():
            chunks.append(Chunk(path.name, doc_title, "\n".join(lines).strip()))
    return chunks


class KnowledgeBase:
    def __init__(self, folder: Path, k1: float = 1.4, b: float = 0.75):
        self.chunks = load_chunks(folder)
        if not self.chunks:
            raise RuntimeError(f"No knowledge found in {folder}")
        self.k1, self.b = k1, b
        # titles count twice so headings like "Products" weigh more
        self.docs = [tokenize(c.title + " " + c.title + " " + c.text) for c in self.chunks]
        self.avgdl = sum(len(d) for d in self.docs) / len(self.docs)
        n = len(self.docs)
        df: dict[str, int] = {}
        for d in self.docs:
            for term in set(d):
                df[term] = df.get(term, 0) + 1
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def _score(self, query: list[str], doc: list[str]) -> float:
        score, dl = 0.0, len(doc)
        for term in set(query):
            tf = doc.count(term)
            if tf:
                idf = self.idf.get(term, 0.0)
                score += idf * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return score

    def search(self, question: str, top_k: int = 4, min_score: float = 0.3) -> list[tuple[Chunk, float]]:
        query = tokenize(question, expand=True)
        if not query:
            return []
        ranked = sorted(((c, self._score(query, d)) for c, d in zip(self.chunks, self.docs)),
                        key=lambda x: x[1], reverse=True)
        best = ranked[0][1] if ranked else 0
        cutoff = max(min_score, best * 0.35)   # keep sections that are reasonably close to the best one
        return [(c, s) for c, s in ranked[:top_k] if s >= cutoff]