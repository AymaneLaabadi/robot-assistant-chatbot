from langgraph.graph import StateGraph, START, END
from models import State
from services.stt import SpeechToTextService
from services.rag import RAGService
from services.llm import LLMService


class Workflow:

    def __init__(self):
        self.stt_service = SpeechToTextService()
        self.rag_service = RAGService()
        self.llm_service = LLMService()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        graph = StateGraph(State)

        graph.add_node("stt", self._stt_step)
        graph.add_node("rag", self._rag_step)
        graph.add_node("llm", self._llm_step)

        graph.add_edge(START, "stt")
        graph.add_edge("stt", "rag")
        graph.add_edge("rag", "llm")
        graph.add_edge("llm", END)

        return graph.compile()

    def _stt_step(self, state: State) -> State:
        text = self.stt_service.transcribe(state.audio_input)
        state.user_query = text
        return state

    def _rag_step(self, state: State) -> State:
        docs = self.rag_service.retrieve(state.user_query)
        state.retrieved_docs = docs
        return state


    def _llm_step(self, state: State) -> State:
        answer = self.llm_service.generate(
            query=state.user_query,
            context=state.retrieved_docs
        )
        state.response = answer
        return state

    def run(self, audio: bytes) -> str:
        initial_state = State(audio_input=audio)
        final_state = self.workflow.invoke(initial_state)
        return final_state.response
