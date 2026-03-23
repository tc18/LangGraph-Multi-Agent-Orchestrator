import chromadb
from sentence_transformers import SentenceTransformer

# Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# ChromaDB client
client = chromadb.PersistentClient(path="./../project1/chroma_db")

collection = client.get_collection("_docs")
