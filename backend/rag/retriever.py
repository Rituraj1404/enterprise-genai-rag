import faiss
import numpy as np
from rag.loader import load_documents
from rag.embeddings import get_embeddings

documents = []
index = None
embedding_model = get_embeddings()

ROLE_HIERARCHY = {
    "intern": 1,
    "manager": 2,
    "admin": 3
}

def build_vectorstore():
    global documents, index

    documents = load_documents()
    texts = [doc.page_content for doc in documents]

    if len(texts) == 0:
        raise RuntimeError(
            "No documents loaded. "
            "Check data/ folder and .txt files."
        )

    vectors = embedding_model.encode(texts)
    vectors = np.array(vectors).astype("float32")

    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(vectors)

    ''' def retrieve_documents(query: str, user_role: str, k: int = 4):
    global index, documents

    if index is None:
        build_vectorstore()

    query_vector = embedding_model.encode([query])
    query_vector = np.array(query_vector).astype("float32")

    _, indices = index.search(query_vector, k)

    results = []
    for idx in indices[0]:
        doc = documents[idx]
        if ROLE_HIERARCHY[user_role] >= ROLE_HIERARCHY[doc.metadata["role"]]:
            results.append(doc)

    return results'''

def retrieve_documents(query: str, user_role: str, k: int = 4):
    global index, documents

    if index is None:
        build_vectorstore()

    query_vector = embedding_model.encode([query])
    query_vector = np.array(query_vector).astype("float32")

    _, indices = index.search(query_vector, k)

    results = []
    for idx in indices[0]:
        doc = documents[idx]
        if ROLE_HIERARCHY[user_role] >= ROLE_HIERARCHY[doc.metadata["role"]]:
            results.append(doc)

    return results
