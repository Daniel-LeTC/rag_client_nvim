# **Polymath Second Brain (RAG CLI)**

A robust, hybrid Retrieval-Augmented Generation (RAG) system designed for managing a "Second Brain" knowledge base. It combines the speed and cost-effectiveness of local embeddings with the reasoning power of Cloud AI (Google Gemini), featuring an automatic fallback to local LLMs (Qwen/Llama) for resilience.

This system implements a "Systematic Chaos" philosophy for note-taking, allowing users to dump information freely while maintaining structured retrieval through intelligent chunking and metadata enrichment.

## **Core Architecture**

* **Hybrid Brain:**  
  * **Primary:** Google Gemini x.y (Cloud API) for high-reasoning tasks and large context understanding.  
  * **Fallback:** Qwen 2.5 7B (Local via Ollama) automatically activates if the cloud service is unreachable or rate-limited.  
* **Local Embeddings:** Uses local embedding models (e.g., maixb-embed-text or nomic-embed-text) via Ollama for fast, free, and private vectorization.  
* **Vector Database:** ChromaDB for persistent vector storage and retrieval.  
* **Reranker:** Integrated BAAI/bge-reranker (Cross-Encoder) to refine search results and improve relevance before feeding them to the LLM.  
* **Enrichment Pipeline:** An automated script (enrich.py) that scans Markdown notes, generates summaries/keywords using AI, and injects metadata directly into the files for better indexing.

## **Features**

### **Systematic Chaos Management**

The system handles two distinct types of notes with specialized chunking strategies:

1. **Daily Logs (YYYYMMDD.md):** Uses Header-based splitting (\#, \#\#) to isolate distinct topics within a single daily dump file.  
2. **Topic Notes:** Uses recursive character splitting for deep-dive technical documents or long-form essays.

### **Contextual Injection**

To prevent semantic confusion in vector space, the enricher injects context into every text chunk:

* **Daily Logs:** Injects the specific Header/Topic path (e.g., DAILY LOG: 20251212 \> TOPIC: Biohacks).  
* **Topic Notes:** Injects global file summaries and keywords.

### **Operational Security**

* API keys are managed via .env files and never hardcoded.  
* Local fallback ensures the system remains functional offline.

## **Prerequisites**

* **Python 3.10+**  
* **uv** (Fast Python package installer and resolver)  
* **Ollama** running locally with the following models pulled:  
  * qwen2.5:7b (or your preferred local LLM)  
  * Embedding model (default is nomic-embed-text, configurable in config.py)

## **Installation**

1. **Clone the repository:**  
   ```
   git clone [https://github.com/Daniel-LeTC/rag_client_nvim.git](https://github.com/Daniel-LeTC/rag_client_nvim.git)  
   cd rag_client_nvim
   ```

2. **Install dependencies using uv:**  
   uv sync

3. Configure Environment Variables:  
   Create a .env file in the root directory:  
   touch .env

   Add your Google Gemini API key:  
   ```
   GOOGLE_API_KEY=your_actual_api_key_here  
   # Optional: Override default note directory  
   # NOTES_DIR=/path/to/your/vault
   ```

4. Verify Configuration:  
   Check config.py to ensure `EMBEDDING_MODEL_NAME` matches your installed Ollama embedding model (e.g., change to nomic-embed if needed).

## **Usage**

### **1. Data Ingestion & Enrichment**

Run the smart runner to scan your notes, generate metadata, and build the vector database. This script handles both enrichment (first run) and incremental updates (subsequent runs based on file hash).

```
uv run smart_run.py
```

*Note: The first run may take time as it generates summaries for all notes.*

### **2. Chat Interface**

The `smart_run.py` script automatically launches the chat interface after ingestion. You can also run it manually:

```
uv run main.py
```

### **3. Resetting the Database**

If you change chunking logic or want a fresh start:

1. Clean metadata from markdown files:  
   `uv run clean_metadata.py`

2. Delete the vector database:  
   `rm -rf chroma_db`

3. Re-run ingestion:  
   `uv run smart_run.py`

## **Project Structure**

* smart_run.py: The orchestrator script. Handles enrichment, git backup (optional), and launching the chat.  
* enrich.py: The data pipeline. Reads Markdown, generates metadata using local AI, chunks text, and loads it into ChromaDB.  
* main.py: The RAG chat interface. Handles retrieval, reranking, and LLM generation (Cloud/Local hybrid).  
* config.py: Centralized configuration for models, paths, and system prompts.  
* clean_metadata.py: Utility to strip AI-generated metadata from source files.

For using in neovim (warning in nvim config nvim you have to use rag_client.lua):

:Ask: Open chat Floating Window.

:Enrich: inject manually Metadata.

:MathPreview: open browser for rendered Markdown (images, latex and code blocks)
