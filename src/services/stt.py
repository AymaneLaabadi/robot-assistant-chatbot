from openai import OpenAI


class SpeechToTextService:
    def __init__(self):
        # Initialize OpenAI client (uses OPENAI_API_KEY from env)
        self.client = OpenAI()

    def transcribe(self, audio_input: bytes | bytearray) -> str:
        if not isinstance(audio_input, (bytes, bytearray)):
            raise ValueError("audio_input must be raw audio bytes.")

        audio_bytes = bytes(audio_input)
        if not audio_bytes:
            raise ValueError("audio_input cannot be empty.")

        file_name, mime_type = self._guess_audio_file_info(audio_bytes)
        transcript = self.client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=(file_name, audio_bytes, mime_type),
        )

        return (transcript.text or "").strip()

    def _guess_audio_file_info(self, audio_bytes: bytes) -> tuple[str, str]:
        if audio_bytes.startswith(b"RIFF"):
            return "audio.wav", "audio/wav"
        if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
            return "audio.webm", "audio/webm"
        if audio_bytes.startswith(b"OggS"):
            return "audio.ogg", "audio/ogg"
        if audio_bytes.startswith(b"ID3") or audio_bytes[:2] == b"\xff\xfb":
            return "audio.mp3", "audio/mpeg"
        if b"ftyp" in audio_bytes[:32]:
            return "audio.m4a", "audio/mp4"
        return "audio.webm", "audio/webm"