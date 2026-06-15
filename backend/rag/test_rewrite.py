import time
from rag.retriever import (
    retrieve_documents,
    rewrite_query,
)

TESTS = [
    "what about interns",
    "leave policy",
    "manager vacation",
    "salary process",
    "project approval flow",
    "work from home"
]

ROLE = "manager"


def run(query):

    print("\n" + "=" * 80)
    print("QUESTION:", query)

    rewritten = rewrite_query(query)

    print("\nREWRITTEN:")
    print(rewritten)

    # WITHOUT rewrite
    t0 = time.time()

    docs_original = retrieve_documents(
        query=query,
        user_role=ROLE,
    )

    normal_time = time.time() - t0

    # WITH rewrite
    t1 = time.time()

    docs_rewritten = retrieve_documents(
        query=rewritten,
        user_role=ROLE,
    )

    rewritten_time = time.time() - t1

    print("\nWITHOUT REWRITE")
    print("Latency:", round(normal_time, 2), "sec")

    for i, d in enumerate(docs_original[:3], 1):
        print(
            f"{i}.",
            d.metadata.get("source"),
            "| rerank:",
            d.metadata.get("rerank_score")
        )

    print("\nWITH REWRITE")
    print("Latency:", round(rewritten_time, 2), "sec")

    for i, d in enumerate(docs_rewritten[:3], 1):
        print(
            f"{i}.",
            d.metadata.get("source"),
            "| rerank:",
            d.metadata.get("rerank_score")
        )


for q in TESTS:
    run(q)