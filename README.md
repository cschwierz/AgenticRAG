# Project Agentic RAG

Agentic RAG with chat interface and internal vector database.

---

## Installation

**Clone Git repository:**

```bash
git config --global http.sslVerify false

git clone [https://git.fft-it.de/cs40004/LogfileAnalyzer.git](https://github.com/cschwierz/AgenticRAG.git)

git config --global http.sslVerify true

cd LogfileAnalyzer/

```

*add agent-chat-ui to workspace*

```bash
git clone https://github.com/langchain-ai/agent-chat-ui.git

cd agent-chat-ui/

pnpm install

pnpm exec next telemetry disable
```

*for further documentation visit [Agent Chat UI](https://docs.langchain.com/oss/python/langchain/ui) on LangChain Docs*

**Set variables** `DB_PATH` & `DOCUMENT_PATH` in rag-pipeline/ chroma-db/ and langgraph-server/ in all .py scripts (or .env files) to your device.

**Install software (LangChain, Ollama on Linux):**

(requires Python 3.10-3.13; Nodejs 18+)

```bash
pip install -U langchain langgraph langgraph-cli langchain-chroma langchain-ollama langchain-community

curl -fsSL https://ollama.com/install.sh | sh

```
*for further documentation visit [Install LangChain](https://docs.langchain.com/oss/python/langchain/install) & [Install LangGraph](https://docs.langchain.com/oss/python/langgraph/install) on LangChain Docs or [Download Ollama](https://ollama.com/download)*

**Download models on ollama:** 

```bash
ollama pull gemma4

ollama pull embeddinggemma
```

If you want to use other models, dont forget to adjust `model` & `EMBEDDING_MODEL` in rag-pipeline/ chroma-db/ and langgraph-server/ in all .py scripts (or .env files)

**Dependencies:** 

rag-pipeline/ chroma-db/ and langgraph-server/ need these dependencies in their `pyproject.toml`:

`uv add langchain langchain-core langchain-community langchain-ollama langgraph langgraph-cli[inmem] langchain-text-splitters langchain-chroma black python-dotenv`

apply the depencencies with `uv sync` as follows:

```bash
cd chroma-db/
uv sync

cd ../rag-pipeline/
uv sync

cd ../langgraph-server/
uv sync --dev

# if sync on langgraph-server fails. do this:

uv venv --python 3.13
source .venv/bin/activate
uv sync --dev
```

## Components:

**rag-pipeline/** raw agentic RAG framework. it can be used to make single queries in the terminal

**langgraph-server/** contains the rag-pipeline/ framework and is hosting the agent for the chat interface

**chroma-db/** contains a persistant vector database and a script `ingestion_example.py` to add documents to the db

**agent-chat-ui/** server for chat interface, connecting with langgraph-server/, client running in Browser

## Usage

**chroma-db**

Open `ingestion_example.py` in an editor and set `DOCUMENT_PATH` to the document,that needs to be added to the DB.

Save and execute the script.

**agent-chat-ui** in a terminal:

```bash
cd agent-chat-ui/

pnpm dev
```

The chat interface can be accessed via the Browser on `http://localhost:3000`

When running the Server for the first time, you need to enter the Agent/Graph-ID: `rag_agent`

**langgraph-server** in a new terminal:

```bash
cd langgraph-server/

uv run langgraph dev
```

## ToDo:

- Dokumentation
- chroma-db skript zum erstellen & pflegen
- .env globale Variablen (?)
- modelle testen
- suchmethode testen
- prompt engineering
- image implementation
- multi agent + adaptive agent rag implementation

- readme.md beschreibt die Anwendung vom Repository
- info.md beschreibt die Architektur
