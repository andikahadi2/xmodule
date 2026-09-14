from app.providers.tts.base import TTSProvider, TTSProviderError
from app.providers.tts.cloud import CloudTTSProvider
from app.providers.tts.local import LocalTTSProvider

__all__ = ["TTSProvider", "TTSProviderError", "CloudTTSProvider", "LocalTTSProvider"]


def get_tts_provider(name: str = "cloud") -> TTSProvider:
    if name == "cloud":
        return CloudTTSProvider()
    if name == "local":
        return LocalTTSProvider()
    raise ValueError(f"Unknown TTS provider: {name}")
