# LogfileAnalyzer Agent Setup & Usage

Agentic RAG with chat interface specialized for analysis on Logfiles.

*This repo is a sanitized copy of my Bachelor Praxisphase. In order to use it, you need to configure "Data Schema" in the parser and prompts to your specific Logfiles and add few shot examples. Unfortunatelly Data Schema is not locally defined, but distributed over the Workspace*

**Current State of LogfileAnalyzer**:

graph-framework/ is the same as in branch multi-agentic-adaptive-rag-1

langgraph-server/ has the following changes:

- the ingest and retrieve functions have been replaced by an implementation from chatgpt
- the reflect node has been reduced to a boolean that checks if the agent gave the final answer.
- MAX & MIN_ITERATIONS have been disabled
- reflect node has been added to the subagent
- subagent now can see the messages state when invoked as classify B

Known Bugs & Fehler in Logfile Analyzer Agent stand 17.06.2026
-	Ingestion parser nicht anpassbar (auf logfile & query)
-	Retrieve tool returns entweder zu viel oder kein context
-	Architektur gpt retrieve tool unbekannt
-	Reflect endless loop


---

## TOC:

[Installation](#installation)

[Usage](#usage)

[Troubleshooting](#troubleshooting)

## Installation

**Clone Git repository:**

```bash
git config --global http.sslVerify false

git clone https://git.fft-it.de/cs40004/LogfileAnalyzer.git

git config --global http.sslVerify true

cd LogfileAnalyzer/

```

**add agent-chat-ui to workspace**

```bash
git clone https://github.com/langchain-ai/agent-chat-ui.git

cd agent-chat-ui/

pnpm install

pnpm exec next telemetry disable
```

> *for further documentation visit [Agent Chat UI](https://docs.langchain.com/oss/python/langchain/ui) on LangChain Docs*

**add mod to agent-chat-ui**

from `mod-agent-chat-ui/` copy and paste `index.tsx` and `use-file-upload.tsx` inside agent-chat-ui to the following paths:

```
agent-chat-ui\src\components\thread\index.tsx

agent-chat-ui\src\hooks\use-file-upload.tsx
```

**Set variables & filepaths:**

In `config.json` and `config_win.json` set the absolute filepaths to every variable.

From langgraph-server/ in all .py scripts in the `# --- Config ---` section set the absolute filepath to `config.json` or `config_win.json` 

> (*graph-framework/, prompt-engineer/ and qa_generator/ are not needed to run the Agent, however, these folders are for testing and prompt generating. Setting up these folders is completely optional*)

**Install software (LangChain, Ollama on Linux):**

(requires Python 3.10-3.13; Nodejs 18+)

```bash
pip install -U langchain langgraph langgraph-cli langchain-chroma langchain-ollama langchain-community

curl -fsSL https://ollama.com/install.sh | sh

```
> *for further documentation visit [Install LangChain](https://docs.langchain.com/oss/python/langchain/install) & [Install LangGraph](https://docs.langchain.com/oss/python/langgraph/install) on LangChain Docs or [Download Ollama](https://ollama.com/download)*

**Download models on ollama:** 

```bash
ollama pull gemma4:31b

ollama pull qwen3.6:35b 
```

If you want to use other models, dont forget to adjust `LLM_MODEL` in the config file

**Dependencies:** 

langgraph-server/, graph-framework/, prompt-engineer/ and qa_generator/ need these dependencies in their `pyproject.toml`:

`uv add langchain langchain-core langchain-community langchain-ollama langgraph langgraph-cli[inmem] langchain-text-splitters langchain-chroma black python-dotenv`

apply the depencencies with `uv sync` as follows:

```bash
cd prompt-engineer/
uv sync

cd ../qa_generator/
uv sync

cd ../graph-framework/
uv sync

cd ../langgraph-server/
uv sync --dev

# if sync on langgraph-server fails. do this:

uv venv --python 3.13
source .venv/bin/activate
uv sync --dev
```


## Usage

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

uv run langgraph dev --no-reload --no-browser
```

**Manual**

In the chat ui type `/manual` or click on `Manual` to open the User Manual 

## Troubleshooting

If the Agent seems to get stuck in generating and the `Cancel` button doesnt react, first try restart the agent-chat-ui server.

- Stop and restart the server in the terminal: 1. `ctrl + C` 2. `pnpm dev`
- Wait till the server is up and reload the ,page in the Browser

If a server restart doesnt help, you must reset the langgraph-server:

- Stop the server in the terminal by spamming `ctrl + C`
- Navigate to .../LogfileAnalyzer/langgraph-server/
- Delete the .langgraph_api/ folder
- Restart the server in the terminal: `uv run langgraph dev --no-reload --no-browser`
- Reopen the agent-chat-ui in the browser with the root URL `localhost:3000`

Note: all threads and messages get deleted during this process.

## ToDo:

- ==Dokumentation==


- [ ] readme.md beschreibt die Anwendung vom Repository
- [x] info.md beschreibt die Architektur
- [ ] prompt architektur dokumentieren

term
: definition

