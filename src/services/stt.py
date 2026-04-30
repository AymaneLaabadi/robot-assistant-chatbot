import json
import os
import re
import unicodedata
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


def _sanitize_term(term: str) -> str:
    """Strip accents and punctuation so AssemblyAI's word_boost accepts it.

    AssemblyAI's word_boost validator is strict: only ASCII alphanumerics
    and single spaces, and at most 6 words per phrase. Special characters
    (apostrophes, accents, commas) cause the entire transcribe call to be
    rejected.
    """
    if not term:
        return ""
    # Strip diacritics (é → e, à → a, …)
    decomposed = unicodedata.normalize("NFD", term)
    ascii_only = "".join(
        c for c in decomposed if unicodedata.category(c) != "Mn"
    )
    # Keep ASCII letters and digits; turn anything else into spaces
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", ascii_only).strip()
    # Cap to 6 words (AssemblyAI limit)
    parts = cleaned.split()
    if len(parts) > 6:
        return ""
    return " ".join(parts)


def _build_word_boost(locations_file: str) -> list[str]:
    """Merge static campus vocabulary with the dynamic locations list.

    AssemblyAI accepts up to ~1000 boost terms; we keep things well under
    that, deduplicated case-insensitively. Each term is sanitized to the
    ASCII subset the API requires.
    """
    seen: set[str] = set()
    result: list[str] = []
    for raw in _CAMPUS_VOCABULARY + _load_location_terms(locations_file):
        term = _sanitize_term(raw)
        if not term:
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(term)
    return result[:300]  # safe margin under the API cap


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
        )

        # Plain config used as a fallback if the boosted config triggers a
        # server-side validation error (different SDK versions interpret
        # word_boost slightly differently).
        self._fallback_config = aai.TranscriptionConfig(
            speech_models=["universal-3-pro"],
            language_detection=True,
            speaker_labels=True,
        )
        self._boost_disabled = False

        self.transcriber = aai.Transcriber()

    def transcribe(self, audio_bytes: bytes) -> str:
        if not self._boost_disabled:
            try:
                transcript = self.transcriber.transcribe(
                    data=audio_bytes,
                    config=self.config,
                )
                return transcript.text
            except Exception as exc:
                # Latch the failure: every subsequent call goes straight
                # to the unboosted config so we don't waste a round-trip.
                print(
                    f"[STT] word_boost transcribe failed ({exc!r}); "
                    f"falling back to plain config for the rest of this run."
                )
                self._boost_disabled = True

        transcript = self.transcriber.transcribe(
            data=audio_bytes,
            config=self._fallback_config,
        )
        return transcript.text