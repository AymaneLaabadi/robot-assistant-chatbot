from langgraph.graph import StateGraph, START, END
from models import State
from services.stt import SpeachToTextService


class Workflow:

    def __init__(self):
        self.stt_service = SpeachToTextService()
        self.llm_service = LLMService()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        graph = StateGraph(State)
        graph.add_edge(START, self._stt_step)
        graph.add_edge(self._stt_step, self._llm_step)
        graph.add_edge(self._llm_step, END)

        return graph.compile()
    
    def _stt_step(self, state: State):
        return 0
    
    def _llm_step(self, state: State):
        return 0
    
    def run(self, query: str) -> State:
        initial_state = State(user_query=query)
        final_state = self.workflow.run(initial_state)
        return final_state.response


