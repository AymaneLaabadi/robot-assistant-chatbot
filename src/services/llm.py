# services/llm.py
class LLMService:
    def generate(self, query: str, context: list[str]) -> str:
        prompt = f"""
        Answer the question using the context below.

        Context:
        {chr(10).join(context)}

        Question:
        {query}
        """
        return "final answer from LLM"
