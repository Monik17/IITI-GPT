# chatbot/rag.py
"""
RAG retrieval against the local IIT Indore vector DB (built by the crawler
pipeline: crawler.py + wikipedia_fetch.py + build_vector_db.py).

Kept separate from utils.py so the LangGraph workflow definition in utils.py
stays clean and readable — this file owns every embedding-model / ChromaDB
detail, and utils.py just calls into it.
"""
import logging

from django.conf import settings
from langchain.schema import Document

logger = logging.getLogger(__name__)

CHROMA_DB_PATH = getattr(settings, "CHROMA_DB_PATH", "chroma_db")
CHROMA_COLLECTION_NAME = "iit_indore"
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"  # must match the model build_vector_db.py used
RETRIEVAL_TOP_K = 5

# Cosine-distance cutoff (chromadb's default metric). Lower distance = closer
# match. 0.5 keeps genuinely relevant chunks and drops unrelated ones.
RELEVANCE_DISTANCE_THRESHOLD = 0.4

# Question is routed to a live web search instead of the vector DB only when
# it's genuinely time-sensitive — everything else, including questions that
# mention a specific year like "2026-27 admission fee", goes to the local
# vector DB first, since the crawled data already covers current-year info.
RECENCY_KEYWORDS = [
    "today", "right now", "currently", "at the moment", "live",
    "latest news", "this week", "this month", "breaking",
]

# Loaded lazily on first real use (not at import time) so Django management
# commands that import this module (migrate, makemigrations, etc.) don't pay
# the model-load cost unnecessarily.
_embedding_model = None
_chroma_collection = None


def _get_components():
    global _embedding_model, _chroma_collection
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model {EMBEDDING_MODEL_NAME} (first call only)...")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    if _chroma_collection is None:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _chroma_collection = client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
    return _embedding_model, _chroma_collection


def retrieve_documents(question: str, top_k: int = RETRIEVAL_TOP_K):
    """Query the local IIT Indore vector DB. Returns a list of langchain
    Document objects, each with a 'relevance_distance' in its metadata."""
    model, collection = _get_components()
    query_embedding = model.encode([question], normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=top_k)

    documents = []
    doc_texts = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    for doc_text, meta, dist in zip(doc_texts, metadatas, distances):
        documents.append(Document(
            page_content=doc_text,
            metadata={**(meta or {}), "relevance_distance": dist},
        ))

    logger.info(f"Retrieved {len(documents)} chunks from local vector DB")
    return documents


def filter_relevant(
    documents,
    threshold: float = RELEVANCE_DISTANCE_THRESHOLD
    ):
    """
    Keep only genuinely relevant ChromaDB documents.

    Lower cosine distance = better semantic match.

    Web-search documents do not contain relevance_distance,
    so they are kept unchanged.
    """

    filtered = []

    for doc in documents:

        # Only ChromaDB documents have relevance_distance
        if isinstance(doc, Document):

            distance = doc.metadata.get("relevance_distance")

            if distance is not None and distance <= threshold:

                filtered.append(doc)

        else:
            # Web-search result
            filtered.append(doc)

    logger.info(
        "Kept %d/%d documents after relevance filtering",
        len(filtered),
        len(documents)
    )

    return filtered


def is_recency_sensitive(question: str) -> bool:
    """True if the question is about something that changes day-to-day
    (today's events, live status) and should skip the vector DB in favor
    of a live web search."""
    q = (question or "").lower()
    return any(kw in q for kw in RECENCY_KEYWORDS)


def build_context(documents) -> str:
    """Turn retrieved/searched documents (Document objects from the vector DB,
    or Tavily's dict-shaped web results) into one context string for the LLM
    prompt, preserving source URLs so the answer can cite them."""
    parts = []
    for doc in documents:
        content, source = _extract_content_and_source(doc)
        parts.append(f"[Source: {source}]\n{content}" if source else content)
    return "\n\n---\n\n".join(parts) if parts else "No context available."


def _extract_content_and_source(doc):
    if isinstance(doc, Document):
        return doc.page_content, doc.metadata.get("url", "")
    if isinstance(doc, dict):
        return doc.get("content", str(doc)), doc.get("url", "")
    return str(doc), ""
