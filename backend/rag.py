from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .database import get_connection


@dataclass
class RAGAnswer:
    answer: str
    sources: List[Dict[str, str]]


def _load_docs():
    conn = get_connection()
    try:
        rows = conn.execute('SELECT id, title, event_type, content, source FROM knowledge_docs').fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def answer_query(query: str, event_type: Optional[str] = None) -> RAGAnswer:
    docs = _load_docs()
    if event_type:
        docs = [doc for doc in docs if doc['event_type'] in {event_type, 'general'}] or docs

    corpus = [doc['content'] for doc in docs]
    vectorizer = TfidfVectorizer(stop_words='english')
    matrix = vectorizer.fit_transform(corpus)
    q_vec = vectorizer.transform([query])
    sims = cosine_similarity(q_vec, matrix)[0]
    top_indices = sims.argsort()[::-1][:2]
    top_docs = [docs[i] for i in top_indices if sims[i] > 0]
    if not top_docs:
        return RAGAnswer(
            answer='No strong knowledge match was found. Try asking a more specific question about timeline, budgeting, or vendor selection.',
            sources=[],
        )

    answer = ' '.join(f"{doc['title']}: {doc['content']}" for doc in top_docs)
    sources = [{'title': doc['title'], 'source': doc['source']} for doc in top_docs]
    return RAGAnswer(answer=answer, sources=sources)
