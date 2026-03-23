# LangGraph Multi-Agent Orchestrator 🤖
Note: This project is part of my journey learning AI Agents and LangGraph!
#

A research and network troubleshooting assistant built with **FastAPI**, **LangGraph**, and **Ollama**. This project uses a "Supervisor" architecture to intelligently route tasks between specialized agents (Math, Network, and RAG Research) while streaming real-time updates to the frontend.

## 🌟 Key Features

* **Multi-Agent Coordination:** A supervisor node evaluates user intent and delegates tasks to specialized workers.
* **Real-Time Streaming:** Uses `astream_events` and Server-Sent Events (SSE) to stream agent "thoughts" and tool outputs (like hop-by-hop network traces) as they happen.
* **Local RAG (Retrieval-Augmented Generation):** Integrated with **ChromaDB** and `sentence-transformers` for private document querying.
* **Specialized Tools:**
    * **Network Tracer:** Simulates real-time path tracing between IPs.
    * **Calculator:** Handles dynamic math expressions via Python's logic.
    * **RAG Search:** Queries a local vector store for company-specific information.

## 🛠️ Tech Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/)
- **Orchestration:** [LangGraph](https://langchain-ai.github.io/langgraph/) & [LangChain](https://python.langchain.com/)
- **LLM:** [Ollama](https://ollama.com/) (Running `llama3.1`)
- **Vector DB:** [ChromaDB](https://www.trychroma.com/)
- **Embeddings:** `all-MiniLM-L6-v2`

## 📁 Project Structure

```text
├── main.py              # FastAPI server & API endpoints
├── agent_3.py           # Core LangGraph logic & Supervisor setup
├── db.py                # ChromaDB client & Embedding configuration
├── models.py            # Pydantic data models
├── tools/
│   ├── rag_tool.py      # Logic for vector database searching
│   └── calculator.py    # Logic for mathematical operations
└── chroma_db/           # Local storage for your vector data
```

## 🚀 Getting Started
0. Clone repo: [RAG-serach-chomaDB](https://github.com/tc18/RAG-serach-chomaDB)
    ```bash
    cd ..
    git clone https://github.com/tc18/RAG-serach-chomaDB.git
    ```

1. Prerequisites
    - Python 3.10+
    - Ollama installed and running.
    - Pull the model: ollama pull llama3.1

2. Installation
    ```bash
    # Clone the repo
    git clone https://github.com/tc18/LangGraph-Multi-Agent-Orchestrator.git
    cd LangGraph-Multi-Agent-Orchestrator

    # Install dependencies
    pip install fastapi uvicorn langgraph langchain_ollama chromadb sentence-transformers pydantic
    ```
    in db.py update,
    ```python
    client = chromadb.PersistentClient(path="./../project1/chroma_db")
    ```
    above line to
    ```python
    client = chromadb.PersistentClient(path="./../RAG-serach-chomaDB/chroma_db")
    ```
    because that was the project which creates vectorDB.

    now run the app,
    ```bash
    # Run app
    uvicorn main:app --reload
    ```

## 📡 API Endpoints
1. Stream Agent Updates
    - **URL**: /ask-stream
    - **Method**: POST
    - **Body**: {"question": "Trace the path from 10.0.0.1 to 8.8.8.8"}
    - **Respons**e: text/event-stream (SSE) providing node updates and tool outputs in real-time.

## 🧠 Design Pattern: The Supervisor
This project follows the Supervisor Design Pattern. Instead of a linear chain, the "Supervisor" node acts as a manager. It receives the user input, looks at the conversation history, and decides whether to call the Network Agent, the Math Agent, or FINISH the conversation.
