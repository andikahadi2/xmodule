from app.providers.tts.base import TTSProvider, TTSProviderError


class LocalTTSProvider(TTSProvider):
    """Placeholder for an offline TTS engine. Not implemented yet — no offline id-ID voice chosen."""

    name = "local"

    async def synthesize(self, text: str, output_path: str, *, voice: str, language: str) -> float:
        raise TTSProviderError("LocalTTSProvider is not implemented yet; use CloudTTSProvider")
