# --- Imports ---

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
import os

# --- Config ---

# - retrieve_db -
DB_PATH = r"/home/path/to/workspace/AgenticRAG/chroma-db/db"
DB_COLLECTION = "data_collection"
TOP_K = 5
EMBEDDING_MODEL = "embeddinggemma"

# - agent -
model = ChatOllama(model="gemma4", temperature=0)
SYSTEM_PROMPT = (
    "STRICT RULES — you must follow these exactly:\n"
    "1. You are a helpful assistant.\n"
    "2. You have access to a database tool called retrieve_db. \n"
    "	Always use the database to retrieve informations from it.\n"
    "3. If you use relevant informations from the database for your answer, then you must answer in the following Markdown Format:\n"
    "{\n"
    "**Source:** {metadata of the chunk with relevant information}\n"
    "**Quote:**\n"
    "	{chunk with relevant information}\n"
    "**End Quote**\n"
    "## Answer:\n"
    "}\n"
    "4. Always use retrieve_db multiple times with different queries.\n"
    "5. If you cant find relevant Information inside the database, refer to your internal Knowledge for the answer.\n"
    "	In this case Mention in your answer, that you havent found relevant information in the database.\n"
)

# --- Tools ---

@tool
def retrieve_db(query: str) -> str:
    """takes a search query and retrieves relevant chunks of data from the Database, based on the query.
    Returns a formatted string containing the metadata and content of the Logdata."""
    #print(f"\n[DEBUG] Tool call: retrieve(query='{query}')\n")

    # - Setup -
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    vector_store = Chroma(
        collection_name=DB_COLLECTION,
        embedding_function=embeddings,
        persist_directory=DB_PATH
    )

    # - Execution -
    results = vector_store.similarity_search_by_vector(
        embedding=embeddings.embed_query(query),
        k=TOP_K,
    )

    # - Parsing -
    retrieval_summary = []
    
    for i, doc in enumerate(results):
        source_info = doc.metadata.get('source', 'Unknown Source')
        content = doc.page_content.strip()
        
        #print("=" * 60)
        #print(f"\n[DEBUG] Search Result: Chunk {i+1}:")
        #print(f"  Source: {source_info}")
        #print(f"  Content:\n\n{content}\n")
        
        summary_block = (
            f"\n--- Chunk {i+1} ---\n"
            f"Source: {source_info}\n"
            f"Content: {content}\n"
        )
        retrieval_summary.append(summary_block)
    
    #print(f"[DEBUG] Retrieved {len(results)} chunks")
    #print("[DEBUG] Done.")
    
    final_result_string = "\n".join(retrieval_summary)
    return final_result_string

# --- Setup ---
graph = create_agent(
    model,
    tools=[retrieve_db],
    system_prompt=SYSTEM_PROMPT,
    debug=False,
    name="rag_agent"
)