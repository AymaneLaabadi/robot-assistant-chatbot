import os
import re

import assemblyai as aai
from dotenv import load_dotenv

load_dotenv(override=True)

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")


# ─────────────────────────── transcript post-processing ─────────────────────
#
# AssemblyAI doesn't know that "EMINES" is a proper noun, so it picks the
# closest English word it knows ("Emile", "Eminem", …) regardless of the
# user's language. We rewrite those after the fact. The patterns are
# language-agnostic — they fire whether the surrounding sentence is FR,
# EN or AR — because the mishearing is purely acoustic.
#
# Add a new line here whenever you spot another consistent mishearing.

_EMINES_FIXUPS = re.compile(
    r"\b("
    r"emile|emiles|"
    r"emin|emins|emine|emines|"
    r"emi[lkn]?ess|"
    r"amines|"
    r"eminem|"
    r"i\s*mines?|ay\s*mines?|a\s*mines?|"
    r"إيميل|إيمين|إيمينس"           # Arabic mishearings of EMINES
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