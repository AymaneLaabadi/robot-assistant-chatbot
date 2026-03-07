import os
import json
from typing import List
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

class RAGService:
    
    def __init__(self, db_path: str = "./vector_db", model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.embeddings = HuggingFaceEmbeddings(
                    model_name=model_name,
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
        
        self.vector_db = None
        index_file = os.path.join(db_path, "index.faiss")
        if os.path.exists(index_file):
            self.vector_db = FAISS.load_local(
                self.db_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )

    def ingest_files(self, file_paths: List[str]):
        """Takes a list of .txt and .pdf paths, chunks them, and stores in DB."""
        all_docs = []
        
        for file_path in file_paths:
            if file_path.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
            elif file_path.endswith('.txt'):
                loader = TextLoader(file_path)
            else:
                continue
            all_docs.extend(loader.load())

        self._ingest_documents(all_docs)

    def ingest_json(self, json_path: str):
        """Ingest documents from a JSON file with 'content', 'url', 'title' fields."""
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)
        docs = [
            Document(page_content=d['content'], metadata={'url': d.get('url', ''), 'title': d.get('title', '')})
            for d in data if d.get('content')
        ]
        self._ingest_documents(docs)

    def _ingest_documents(self, docs: List[Document]):
        """Chunk, embed, and store documents."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(docs)

        self.vector_db = FAISS.from_documents(
            documents=chunks,
            embedding=self.embeddings,
        )
        os.makedirs(self.db_path, exist_ok=True)
        self.vector_db.save_local(self.db_path)
        print(f"Successfully indexed {len(chunks)} chunks.")

    def search(self, query: str, k: int = 3) -> List[Document]:
            """Embeds the query and returns the top k relevant chunks."""
            if not self.vector_db:
                return []
            
            return self.vector_db.similarity_search(query, k=k)