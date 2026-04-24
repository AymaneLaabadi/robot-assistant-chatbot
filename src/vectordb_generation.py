from services.rag import RAGService
ingest_files = RAGService().ingest_files

file_paths = [
    "data/CPI EMINES.pdf",
    "data/Brochure UM6P.pdf",
    "data/cleaned_emines_docs.json"
]
ingest_files(file_paths)