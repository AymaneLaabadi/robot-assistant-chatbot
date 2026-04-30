import os
import re

import assemblyai as aai
from dotenv import load_dotenv

load_dotenv(override=True)

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")


# ─────────────────────── transcript post-processing ─────────────────────────
#
# AssemblyAI doesn't know "EMINES" or "UM6P" as words, so on short audio it
# picks the closest thing it does know — "Emile", "Eminem", "amines", or
# "U M six P". We rewrite those mishearings to the canonical campus terms
# *after* transcription, regardless of detected language. The pure regex
# approach avoids any AssemblyAI SDK feature that might fail on different
# versions (we tried word_boost / custom_spelling and both broke transcription
# entirely on certain SDK builds).
#
# Add new mishearings here as you observe them in production.

_EMINES_FIXUPS = re.compile(
    r"\b("
    r"emile|emiles|"
    r"emin|emins|emine|emines|"
    r"emi[lkn]?ess|"
    r"amines|"
    r"eminem|"
    r"i\s*mines?|ay\s*mines?|a\s*mines?|"
    r"إيميل|إيمين|إيمينس"            # Arabic mishearings of EMINES
    r")\b",
    flags=re.IGNORECASE | re.UNICODE,
)
_UM6P_FIXUPS = re.compile(
    r"\b(?:u\s*m\s*6\s*p|um\s*six\s*p|you\s*m\s*six\s*p)\b",
    flags=re.IGNORECASE,
)


def _postprocess(text: str) -> str:
    if not text:
        return text
    text = _EMINES_FIXUPS.sub("EMINES", text)
    text = _UM6P_FIXUPS.sub("UM6P", text)
    return text


class SpeechToTextService:

    def __init__(self):
        self.config = aai.TranscriptionConfig(
            speech_models=['universal-3-pro'],
            language_detection=True,
            speaker_labels=True,
        )
        self.transcriber = aai.Transcriber()

    def transcribe(self, audio_bytes: bytes) -> str:
        transcript = self.transcriber.transcribe(
            data=audio_bytes,
            config=self.config
        )
        return _postprocess(transcript.text or "")