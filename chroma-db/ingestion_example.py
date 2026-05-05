# Dokumentation 
#   https://reference.langchain.com/python/langchain-core/vectorstores/in_memory/InMemoryVectorStore
#   https://docs.langchain.com/oss/python/integrations/vectorstores/chroma
# In this script, data is being indexed and saved into a Chroma vector store

import os
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders.onedrive_file import CHUNK_SIZE
from langchain_text_splitters import CharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

DOCUMENT_PATH = r"/home/path/to/my-data.md"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 0
DB_PATH = r"/home/path/to/workspace/AgenticRAG/chroma-db/db"
DB_COLLECTION = "data_collection"
MODEL = "embeddinggemma"

if __name__ == "__main__":

    print("Loading Document...")
    loader = TextLoader(DOCUMENT_PATH)
    document = loader.load()

    print("Splitting Document into Chunks...")
    text_splitter = CharacterTextSplitter(separator="\n", chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = text_splitter.split_documents(document)
    print(f"created {len(chunks)} chunks")

    print("Setting up...")
    embeddings = OllamaEmbeddings(model=MODEL)
    vector_store = Chroma(
        collection_name=DB_COLLECTION,
        embedding_function=embeddings,
        persist_directory=DB_PATH
    )
    
    print("Ingesting...")
    vector_store.add_documents(chunks)

    print("Done.")