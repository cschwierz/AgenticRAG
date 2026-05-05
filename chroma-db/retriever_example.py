# Dokumentation 
#   https://reference.langchain.com/python/langchain-core/vectorstores/in_memory/InMemoryVectorStore
#   https://docs.langchain.com/oss/python/integrations/vectorstores/chroma
# In this script, data is being retrieved from a Chroma vector store via one query

import os
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

DB_PATH = r"/home/path/to/workspace/AgenticRAG/chroma-db/db"
DB_COLLECTION = "data_collection"
MODEL = "embeddinggemma"
TOP_K = 5
QUERY = (
    "Search query for database"
)

if __name__ == "__main__":

    print("Setting up...")
    embeddings = OllamaEmbeddings(model=MODEL)
    vector_store = Chroma(
        collection_name=DB_COLLECTION,
        embedding_function=embeddings,
        persist_directory=DB_PATH
    )

    print("Retrieving...")
    results = vector_store.similarity_search_by_vector(
        embedding=embeddings.embed_query(QUERY),
        k=TOP_K,
    )

    for doc in results:
        print("=" * 60)
        print(f"\n[SEARCH RESULT] Source: [{doc.metadata}]\nContent:\n\n{doc.page_content}\n")
        print(f"retrieved {len(results)} chunks")
        print("done")