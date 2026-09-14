import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audio import AudioAsset
from app.models.content import Content
from app.models.script import ContentScript
from app.providers.tts import get_tts_provider
from app.providers.tts.cloud import DEFAULT_VOICES


async def generate_audio(
    db: Session, content: Content, script: ContentScript, provider_name: str = "cloud"
) -> AudioAsset:
    provider = get_tts_provider(provider_name)
    voice = DEFAULT_VOICES.get(settings.default_language, "id-ID-GadisNeural")

    audio_dir = Path(settings.storage_path) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{content.id}_{uuid.uuid4().hex}.mp3"
    dest = audio_dir / filename

    duration = await provider.synthesize(
        script.script_text, str(dest), voice=voice, language=settings.default_language
    )

    asset = AudioAsset(
        content_id=content.id,
        provider=provider.name,
        voice=voice,
        language=settings.default_language,
        file_path=str(dest),
        duration=duration,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset
