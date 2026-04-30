import json
import os
from pathlib import Path

import assemblyai as aai
from dotenv import load_dotenv

load_dotenv(override=True)

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")


# Domain-specific terms AssemblyAI's generic model otherwise mishears or
# discards (proper nouns, acronyms, French phrases that look like noise to
# an EN-trained model). Anything in this list gets a transcription bias
# via the AssemblyAI `word_boost` feature.
_CAMPUS_VOCABULARY = [
    "EMINES",
    "UM6P",
    "Mohammed VI Polytechnique",
    "Polytechnique",
    "Ben Guerir",
    "Cafétéria",
    "Cafeteria",
    "Foyer",
    "Accueil",
    "Administration",
    "Affaires Étudiantes",
    "Bureau d'Aide Financière",
    "Bureau des Admissions",
    "Bureau d'Ordre",
    "Health Center",
    "Laboratoire",
    "Mécatronique",
    "Radio Étudiante",
    "E-tech", "E-olive", "E-mix",
    "Service d'Impression",
    "Station de Recharge",
]


def _load_location_terms(locations_file: str) -> list[str]:
    """Return every canonical name and alias from data/locations.json.

    Failing to load the file should not break the STT — we just lose the
    bonus boost from data-driven names.
    """
    path = Path(locations_file)
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as fh:
            locations = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []

    terms: list[str] = []
    for loc in locations:
        name = (loc.get("location_name") or "").strip()
        if name:
            terms.append(name)
        for alias in loc.get("aliases", []) or []:
            alias = (alias or "").strip()
            if alias:
                terms.append(alias)
    return terms


def _build_word_boost(locations_file: str) -> list[str]:
    """Merge static campus vocabulary with the dynamic locations list.

    AssemblyAI accepts up to a few hundred boost terms; we keep things
    well under that, deduplicated case-insensitively while preserving
    the original casing of the first occurrence.
    """
    seen: set[str] = set()
    result: list[str] = []
    for term in _CAMPUS_VOCABULARY + _load_location_terms(locations_file):
        if not term:
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(term)
    return result


class SpeechToTextService:
    def __init__(self, locations_file: str = "data/locations.json"):
        self.word_boost = _build_word_boost(locations_file)
        self.config = aai.TranscriptionConfig(
            speech_models=["universal-3-pro"],
            language_detection=True,
            speaker_labels=True,
            # Bias the decoder toward our campus vocabulary. Without this
            # AssemblyAI silently rejects very short utterances that are
            # just a proper noun ("EMINES", "UM6P") because it has no
            # confidence on them and ends up returning a null transcript.
            word_boost=self.word_boost,
            boost_param="high",
        )
        self.transcriber = aai.Transcriber()

    def transcribe(self, audio_bytes: bytes) -> str:
        transcript = self.transcriber.transcribe(
            data=audio_bytes,
            config=self.config,
        )
        return transcript.text