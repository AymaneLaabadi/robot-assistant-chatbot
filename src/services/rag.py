# services/rag.py
class RAGService:
    
    def retrieve(self, query: str, k: int = 4):
        return [
            "Document chunk 1",
            "Document chunk 2",
        ]
