import base64
from src.workflow import Workflow


# SINGLE WORKFLOW INSTANCE (avoid reloading every call)
workflow = Workflow(memory_base="./memories")


# MAIN ENTRY POINT (called from Streamlit)
def handle_voice_request(payload: dict) -> dict:
    """
    Process a voice request coming from the frontend component.

    Expected payload:
    {
        "audio_base64": str,
        "mime_type": str,
        "conversation_id": str | None
    }
    """

    try:
        # Decode incoming audio
        audio_base64 = str(payload.get("audio_base64", ""))
        if not audio_base64:
            return {"error": "Empty audio payload."}

        audio_bytes = base64.b64decode(audio_base64)

        conversation_id = payload.get("conversation_id")

        # Run full pipeline (STT → LLM → TTS)
        result = workflow.run_audio(
            audio_bytes,
            conversation_id=conversation_id
        )

        # Build response
        response_payload = {
            "response": _state_value(result, "response") or "",
            "transcription": _state_value(result, "transcription") or "",
            "response_audio_base64": _encode_audio(
                _state_value(result, "response_audio")
            ),
            "response_audio_mime_type": _state_value(
                result,
                "response_audio_format",
                "audio/mp3"
            ) or "audio/mp3",
        }

        return response_payload

    except Exception as exc:
        return {
            "error": str(exc) or "Voice processing failed."
        }


# HELPERS (unchanged logic, just cleaner)
def _state_value(result, key: str, default=None):
    if isinstance(result, dict):
        return result.get(key, default)
    return getattr(result, key, default)


def _encode_audio(audio_bytes: bytes | None) -> str | None:
    if not audio_bytes:
        return None
    return base64.b64encode(audio_bytes).decode("ascii")