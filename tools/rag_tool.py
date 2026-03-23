from langchain.tools import tool
from db import model, collection


@tool
def rag_search(query: str) -> str:
    """
    Search the company internal knowledge base for policies, procedures, and info.
    
    Args:
        query: The natural language search string or question.
    """
    print(query)

    query_embedding = model.encode([query])

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3
    )

    docs = results["documents"][0]
    distances = results["distances"][0]

    print(docs)
    print(distances)

    filtered_docs = [
        doc for doc, dist in zip(docs, distances) if dist < 0.5
    ]

    if not filtered_docs:
        return "No relevant documents found."

    return "\n".join(filtered_docs)
