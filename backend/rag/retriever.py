import faiss
import numpy as np
import pickle
import logging
from pathlib import Path
from rag.loader import load_documents
from rag.embeddings import get_embeddings

logger = logging.getLogger(__name__)

# ── Globals ────────────────────────────────────────────────────────────────────
documents = []
index = None
embedding_model = get_embeddings()

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
def retrieve_documents(
    query:     str,
    user_role: str,
    k:         int = 4,
    fetch_k:   int = 20,
) -> list:
    """
    Retrieve the top-k document chunks accessible to `user_role`.

    Args:
        query:     The user's natural-language question.
        user_role: The authenticated user's role (intern / manager / admin).
        k:         Number of results to return after role filtering.
        fetch_k:   Candidate pool size before filtering (should be >> k).

    Returns:
        List of LangChain Document objects, best match first.
    """
    global index, documents

    if index is None:
        build_vectorstore()

    # Encode + normalise query the same way we did the corpus
    query_vector = embedding_model.encode([query])
    query_vector = np.array(query_vector, dtype="float32")
    faiss.normalize_L2(query_vector)

    # Retrieve a large candidate pool
    scores, indices = index.search(query_vector, min(fetch_k, len(documents)))

    user_level = ROLE_HIERARCHY.get(user_role, 0)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:                        # FAISS padding sentinel
            continue

        doc       = documents[idx]
        doc_level = ROLE_HIERARCHY.get(doc.metadata.get("role", "admin"), 99)

        if user_level >= doc_level:          # role check
            doc.metadata["score"] = round(float(score), 4)   # attach similarity
            results.append(doc)

        if len(results) == k:               # stop once we have enough
            break

    return results