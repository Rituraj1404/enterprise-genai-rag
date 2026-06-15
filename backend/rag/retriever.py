import faiss
import numpy as np
import pickle
import logging
from pathlib import Path
from rag.loader import load_documents, BASE_DATA_PATH
from rag.embeddings import get_embeddings
from groq import Groq
from config import GROQ_API_KEY
groq_client = Groq(
    api_key=GROQ_API_KEY
)

logger = logging.getLogger(__name__)

# ── Globals ────────────────────────────────────────────────────────────────────
documents = []
index = None
embedding_model = get_embeddings()

# Cross-encoder reranker — loaded lazily on first use to avoid slowing startup
_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        logger.info("Loading reranker model (cross-encoder/ms-marco-MiniLM-L-6-v2) …")
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker

# ── Persistence paths ──────────────────────────────────────────────────────────
# Saved next to this file: backend/rag/faiss_store/
STORE_DIR  = Path(__file__).resolve().parent / "faiss_store"
INDEX_PATH = STORE_DIR / "index.faiss"
DOCS_PATH  = STORE_DIR / "documents.pkl"

# ── Role hierarchy ─────────────────────────────────────────────────────────────
ROLE_HIERARCHY = {
    "intern":  1,
    "manager": 2,
    "admin":   3,
}


# ── FIX 1 : Persistent FAISS ───────────────────────────────────────────────────
# Previously the index lived only in RAM.  Every server restart forced a full
# re-encode of all documents (slow, wasteful).  Now we:
#   • Save the FAISS index to disk with faiss.write_index()
#   • Pickle the document list alongside it
#   • Load from disk on the next startup if both files exist
#   • Only rebuild when documents change (pass force_rebuild=True)
# ──────────────────────────────────────────────────────────────────────────────
def build_vectorstore(force_rebuild: bool = False):
    """
    Build (or load) the FAISS vector store.

    Args:
        force_rebuild: If True, ignore any saved index and re-encode from scratch.
                       Use this after adding / updating documents.
    """
    global documents, index

    STORE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load from disk if available and not forcing a rebuild ──────────────────
    if not force_rebuild and INDEX_PATH.exists() and DOCS_PATH.exists():
        logger.info("Loading FAISS index from disk …")
        index     = faiss.read_index(str(INDEX_PATH))
        with open(DOCS_PATH, "rb") as f:
            documents = pickle.load(f)
        logger.info(f"Loaded {len(documents)} document chunks from disk.")
        return

    # ── Build from scratch ─────────────────────────────────────────────────────
    logger.info("Building FAISS index from documents …")
    documents = load_documents()
    texts     = [doc.page_content for doc in documents]

    if not texts:
        raise RuntimeError(
            "No documents loaded. Check the data/ folder for .txt / .pdf files."
        )

    vectors = embedding_model.encode(texts, show_progress_bar=True)
    vectors = np.array(vectors, dtype="float32")

    # Normalise vectors → cosine similarity via IndexFlatIP
    # (more meaningful than raw L2 distance for text)
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])   # Inner-product == cosine after norm
    index.add(vectors)

    # ── Persist to disk ────────────────────────────────────────────────────────
    faiss.write_index(index, str(INDEX_PATH))
    with open(DOCS_PATH, "wb") as f:
        pickle.dump(documents, f)

    logger.info(f"Index built and saved: {len(documents)} chunks, dim={vectors.shape[1]}")


# ── FIX 2 : Better retrieval ───────────────────────────────────────────────────
# Old behaviour:
#   • Search for exactly k=4 vectors globally
#   • Filter by role afterwards
#   • Result: a manager asking a question might get only 1-2 relevant chunks
#     because 2-3 of the top-4 hits were admin-only docs that got filtered out
#
# New behaviour:
#   • Search for fetch_k candidates (default 20) — a much larger pool
#   • Filter by role from that pool
#   • Return the top k after filtering → always k good results (if they exist)
#   • Scores (cosine similarities) are returned so callers can log / threshold
# ──────────────────────────────────────────────────────────────────────────────
# ── PDF upload + reindex ────────────────────────────────────────────────────
# Saves the uploaded PDF into data/<role>_docs/ and rebuilds the FAISS index
# so it becomes searchable immediately (with role metadata from the folder).
def save_and_index_pdf(content: bytes, filename: str, role: str = "admin") -> None:
    role_folder_map = {
        "intern": "intern_docs",
        "manager": "manager_docs",
        "admin": "admin_docs",
    }
    folder_name = role_folder_map.get(role, "admin_docs")
    target_dir = BASE_DATA_PATH / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / filename
    target_path.write_bytes(content)

    logger.info(f"Saved uploaded PDF to {target_path}, rebuilding index …")
    build_vectorstore(force_rebuild=True)
    
def rewrite_query(question: str) -> str:
    """
    Rewrite user query for retrieval.
    """

    try:

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0,
            max_tokens=60,
            messages=[
                {
                    "role": "system",
                    "content": """
Rewrite the user's question into an optimized retrieval query.

Rules:
- Preserve meaning.
- Expand abbreviations.
- Add missing context.
- Return ONLY rewritten query.
- No explanation.
"""
                },
                {
                    "role": "user",
                    "content": question
                }
            ]
        )

        rewritten = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        return rewritten

    except Exception as e:

        logger.warning(
            f"Query rewrite failed: {e}"
        )

        return question


def retrieve_documents(
    query:     str,
    user_role: str,
    k:         int = 4,
    fetch_k:   int = 20,
    rerank_pool: int = 10,
) -> list:
    """
    Retrieve the top-k document chunks accessible to `user_role`.

    Pipeline:
      1. FAISS cosine search over fetch_k candidates (fast, approximate)
      2. Filter by role hierarchy
      3. Take top `rerank_pool` of those and re-score with a cross-encoder
         (slower, but much more accurate at judging query-passage relevance)
      4. Return the top k after reranking

    Args:
        query:       The user's natural-language question.
        user_role:   The authenticated user's role (intern / manager / admin).
        k:           Final number of results to return.
        fetch_k:     Candidate pool size from FAISS before role filtering.
        rerank_pool: How many role-filtered candidates to pass to the reranker.

    Returns:
        List of LangChain Document objects, best match first, with
        metadata["score"] (FAISS cosine) and metadata["rerank_score"]
        (cross-encoder relevance) attached.
    """
    global index, documents

    if index is None:
        build_vectorstore()

    # Encode + normalise query the same way we did the corpus
    original_query = query

    query = rewrite_query(query)

    logger.info(
    f"Query rewrite: '{original_query}' → '{query}'"
        )
    query_vector = embedding_model.encode([query])
    query_vector = np.array(query_vector, dtype="float32")
    faiss.normalize_L2(query_vector)

    # Retrieve a large candidate pool
    scores, indices = index.search(query_vector, min(fetch_k, len(documents)))

    user_level = ROLE_HIERARCHY.get(user_role, 0)

    # ── Stage 1: role-filtered candidates from FAISS ────────────────────────
    candidates = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:                        # FAISS padding sentinel
            continue

        doc       = documents[idx]
        doc_level = ROLE_HIERARCHY.get(doc.metadata.get("role", "admin"), 99)

        if user_level >= doc_level:          # role check
            doc.metadata["score"] = round(float(score), 4)   # FAISS cosine similarity
            candidates.append(doc)

        if len(candidates) == rerank_pool:
            break

    if not candidates:
        return []

    # ── Stage 2: cross-encoder reranking ────────────────────────────────────
    try:
        reranker = _get_reranker()
        pairs = [(query, doc.page_content) for doc in candidates]
        rerank_scores = reranker.predict(pairs)

        for doc, rscore in zip(candidates, rerank_scores):
            doc.metadata["rerank_score"] = round(float(rscore), 4)

        # Sort by reranker score (descending) — this is the final ordering
        candidates.sort(key=lambda d: d.metadata["rerank_score"], reverse=True)
    except Exception as e:
        # If reranker fails to load (e.g. missing dependency), fall back to
        # FAISS ordering so the system still works without it.
        logger.warning(f"Reranking unavailable, falling back to FAISS order: {e}")

    return candidates[:k]