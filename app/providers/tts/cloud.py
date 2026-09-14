import edge_tts

from app.providers.tts.base import TTSProvider, TTSProviderError
from app.utils.ffmpeg import FFmpegError, probe_duration_seconds

DEFAULT_VOICES = {
    "id-ID": "id-ID-GadisNeural",
}


class CloudTTSProvider(TTSProvider):
    """Uses Microsoft Edge's public text-to-speech service (free, no API key)."""

    name = "cloud"

    async def synthesize(
        self, text: str, output_path: str, *, voice: str | None = None, language: str = "id-ID"
    ) -> float:
        resolved_voice = voice or DEFAULT_VOICES.get(language, "id-ID-GadisNeural")
        try:
            communicate = edge_tts.Communicate(text, resolved_voice)
            await communicate.save(output_path)
        except Exception as exc:  # edge_tts raises various network/runtime errors
            raise TTSProviderError(f"Edge TTS synthesis failed: {exc}") from exc

        try:
            return probe_duration_seconds(output_path)
        except FFmpegError:
            return 0.0
