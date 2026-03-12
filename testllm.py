from src.services.llm import LLMService
from src.services.rag import RAGService

rag = RAGService()
llm_service = LLMService(rag)

print(llm_service.generate("EMINES programs"))
