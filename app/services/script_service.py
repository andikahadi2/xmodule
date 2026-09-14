from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content import Content
from app.models.content_idea import ContentIdea
from app.models.script import ContentScript
from app.providers.ai import get_ai_provider
from app.providers.ai.base import AIProviderError
from app.providers.ai.json_utils import extract_json

SCRIPT_PROMPT = """Kamu adalah script writer untuk video affiliate pendek berbahasa Indonesia (9:16, {duration} detik).

Produk: {product_name}
Deskripsi: {product_description}

Ide konten:
- Hook: {hook}
- Angle: {angle}
- Target audience: {target_audience}
- Tipe konten: {content_type}

Buat script dengan struktur berikut (total durasi {duration} detik):
0-3 detik: Hook
3-8 detik: Masalah
8-20 detik: Solusi / perkenalan produk
20-25 detik: Benefit
25-{duration} detik: Call To Action

Jangan membuat klaim produk yang tidak dapat diverifikasi dari deskripsi di atas.
CTA tidak boleh menampilkan link panjang, gunakan kalimat seperti "cek link di bio".

Balas HANYA dengan JSON object valid, tanpa teks lain, dengan field:
script_text (naskah lengkap semua bagian, dipisah baris baru),
hook (kalimat hook saja),
cta (kalimat CTA saja).
"""


def generate_script(db: Session, content: Content, idea: ContentIdea, provider_name: str | None = None) -> ContentScript:
    provider = get_ai_provider(provider_name or settings.ai_provider)

    prompt = SCRIPT_PROMPT.format(
        duration=idea.estimated_duration,
        product_name=content.product.name,
        product_description=content.product.description or "-",
        hook=idea.hook,
        angle=idea.angle,
        target_audience=idea.target_audience,
        content_type=idea.content_type,
    )

    try:
        raw = provider.complete(prompt, json_mode=True)
        data = extract_json(raw)
    except (AIProviderError, ValueError) as exc:
        raise AIProviderError(f"Failed to generate script: {exc}") from exc

    existing_versions = [s.version for s in content.scripts]
    next_version = max(existing_versions, default=0) + 1

    script = ContentScript(
        content_id=content.id,
        version=next_version,
        script_text=data.get("script_text", ""),
        hook=data.get("hook", idea.hook),
        cta=data.get("cta", ""),
        duration=idea.estimated_duration,
        ai_provider=provider.name,
        ai_model=getattr(settings, f"{provider.name}_model", ""),
    )
    db.add(script)
    content.status = "SCRIPT_GENERATED"
    db.commit()
    db.refresh(script)
    return script
