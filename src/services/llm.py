# services/llm_service.py

from typing import Optional, List
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document

from src.services.rag import RAGService

load_dotenv(override=True)


class LLMService:
    def __init__(self, rag_service: RAGService):
        # Initialize RAG service
        self.rag = rag_service

        # Groq model
        self.llm = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0.3,
            max_retries=3,
        )

        # RAG search as a tool
        @tool("document_retriever")
        def retrieval_tool(query: str) -> str:
            """
            Search the internal knowledge base for relevant documents.
            Use this when answering questions about EMINES school programs, UM6P or any related information.
            """
            docs: List[Document] = self.rag.search(query, k=3)

            if not docs:
                return "No relevant documents found."

            return "\n\n".join([doc.page_content for doc in docs])
    
        tools = [retrieval_tool]

        # Agent prompt
        system_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a professional AI assistant for the EMINES school.\n"
                    "You have access to a RAG tool.\n"
                    "When needed, use document_retriever to retrieve relevant information.\n"
                    "Base your answers strictly on retrieved content when possible.\n"
                    "If the information is not found, clearly say so."
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        self.agent = create_agent(self.llm, tools=tools, system_prompt=system_prompt)


    def generate(self, query: str, chat_history: Optional[List[BaseMessage]] = None) -> str:
        messages = [{"role": "user", "content": query}]
        response = self.agent.invoke({"messages": messages})
        return response["output"]
    