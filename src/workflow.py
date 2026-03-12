from langgraph.graph import StateGraph, START, END
from src.models import State
from .services.stt import SpeechToTextService
from .services.rag import RAGService
from .services.llm import LLMService
from .services.memory import MemoryService
from langchain_core.messages import HumanMessage, AIMessage
import uuid


class Workflow:

    def __init__(self, memory_base: str = "./memories"):
        # Services
        self.stt_service = SpeechToTextService()
        self.rag_service = RAGService()
        self.memory_service = MemoryService(base_path=memory_base)

        # LLM gets RAG injected (agentic)
        self.llm_service = LLMService(self.rag_service)

        # Build graph
        self.workflow = self._build_workflow()

    # ---------------------------------------------------
    # GRAPH
    # ---------------------------------------------------

    def _build_workflow(self):
        graph = StateGraph(State)

        graph.add_node("stt", self._stt_step)
        graph.add_node("llm", self._llm_step)

        graph.add_edge(START, "stt")
        graph.add_edge("stt", "llm")
        graph.add_edge("llm", END)

        return graph.compile()

    # ---------------------------------------------------
    # STEPS
    # ---------------------------------------------------

    def _stt_step(self, state: State) -> State:
        if state.audio_input:
            text = self.stt_service.transcribe(state.audio_input)
            state.user_query = text if text else "Could not transcribe audio."
        return state

    def _llm_step(self, state: State) -> State:
        print("--- GENERATING RESPONSE (agentic) ---")

        conv_id = getattr(state, "conversation_id", None)

        # Convert stored memory into LangChain messages
        chat_history = []

        if conv_id:
            stored_messages = self.memory_service.get_messages(conv_id, limit=10)

            for m in stored_messages:
                if m["role"] == "user":
                    chat_history.append(HumanMessage(content=m["text"]))
                elif m["role"] == "assistant":
                    chat_history.append(AIMessage(content=m["text"]))

        # Agentic call (Automatic retrieval + response generation)
        response = self.llm_service.generate(
            query=state.user_query,
            chat_history=chat_history,
            tool_inputs={"query": state.user_query}
        )
        state.response = response

        # Persist memory
        if conv_id:
            self.memory_service.add_message(conv_id, "user", state.user_query or "")
            self.memory_service.add_message(conv_id, "assistant", response or "")

        return state

    # ---------------------------------------------------
    # PUBLIC METHODS
    # ---------------------------------------------------

    def run_text(self, text: str, conversation_id: str = None):
        """
        Run a single text input through the workflow, store in memory,
        and return a plain chat history as a list of dictionaries: {"role": "user|assistant", "content": str}.
        """
        # Initialize state
        state = State(user_query=text, conversation_id=conversation_id)

        # Create memory if conversation_id is provided
        if conversation_id and not self.memory_service.exists(conversation_id):
            self.memory_service.create(conversation_id)

        # --- Generate response ---
        print("--- GENERATING RESPONSE (run_text) ---")
        conv_id = getattr(state, "conversation_id", None)

        # Retrieve last messages from memory and convert to LangChain messages
        chat_history = []
        if conv_id:
            stored_messages = self.memory_service.get_messages(conv_id, limit=10)
            for m in stored_messages:
                if m["role"] == "user":
                    chat_history.append(HumanMessage(content=m["text"]))
                elif m["role"] == "assistant":
                    chat_history.append(AIMessage(content=m["text"]))

        # Generate reply from LLM using the higher-level API (returns a string)
        reply = self.llm_service.generate(query=state.user_query, chat_history=chat_history)

        # Keep raw text (no HTML formatting)
        state.response = reply

        # Persist memory
        if conv_id:
            self.memory_service.add_message(conv_id, "user", text)
            self.memory_service.add_message(conv_id, "assistant", reply or "")

        # --- Prepare output as a list of dicts ---
        history = []
        if conv_id:
            all_mem = self.memory_service.get_messages(conv_id)
            for m in all_mem:
                history.append({
                    "role": m["role"],
                    "content": m["text"]
                })

        # Append latest if not present
        if not history:
            history.append({"role": "assistant", "content": reply or ""})

        return history

    def run(self, audio: bytes, conversation_id: str = None) -> str:
        initial_state = State(audio_input=audio)

        if conversation_id:
            self.memory_service.create(conversation_id)
            setattr(initial_state, "conversation_id", conversation_id)

        final_state = self.workflow.invoke(initial_state)

        return final_state.response