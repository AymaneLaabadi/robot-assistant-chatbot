from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv(override=True)

class LLMService:
    def __init__(self):
        self.llm = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0.3, # Lowered for more factual RAG responses
            max_retries=2
        )
    
    def generate(self, query: str, documents: list) -> str:
        """
        Processes documents into a string and generates a response.
        """
        # Extract page_content from Document objects if they aren't strings yet
        context_text = "\n\n".join(
            [doc.page_content if hasattr(doc, 'page_content') else str(doc) for doc in documents]
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a professional assistant. Use the following context to answer the user's question. If the answer isn't in the context, say you don't know based on the documents, but offer general help if appropriate."),
            ("human", "Context:\n{context}\n\nQuestion: {query}")
        ])

        chain = prompt | self.llm
        
        response = chain.invoke({
            "context": context_text,
            "query": query
        })
        
        return response.content