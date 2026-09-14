from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content import Content
from app.models.content_idea import ContentIdea
from app.models.product import Product
from app.providers.ai import get_ai_provider
from app.providers.ai.base import AIProviderError
from app.providers.ai.json_utils import extract_json

CONTENT_TYPES = [
    "problem_solution",
    "product_demo",
    "comparison",
    "top_list",
    "before_after",
    "tips",
    "review",
    "faq",
]

IDEA_PROMPT = """Kamu adalah content planner untuk video affiliate pendek (9:16, 20-30 detik).
Berdasarkan produk berikut, buat 3 ide konten berbeda dalam format JSON array.

Produk:
- Nama: {name}
- Deskripsi: {description}
- Harga: Rp{price}
- Kategori: {category}

Setiap ide harus punya field: hook, angle, target_audience, content_type, estimated_duration.
content_type harus salah satu dari: {content_types}.
Jangan membuat klaim produk yang tidak dapat diverifikasi dari deskripsi di atas.

Balas HANYA dengan JSON array valid, tanpa teks lain. Contoh format:
[{{"hook": "...", "angle": "...", "target_audience": "...", "content_type": "problem_solution", "estimated_duration": 30}}]
"""


def _score_idea(idea: dict) -> float:
    score = 0.0
    hook = idea.get("hook", "")
    if "?" in hook:
        score += 2
    if idea.get("content_type") == "problem_solution":
        score += 1
    duration = idea.get("estimated_duration", 30)
    if 20 <= duration <= 30:
        score += 1
    return score


def generate_content_ideas(db: Session, product: Product, provider_name: str | None = None) -> Content:
    provider = get_ai_provider(provider_name or settings.ai_provider)

    prompt = IDEA_PROMPT.format(
        name=product.name,
        description=product.description or "-",
        price=product.price,
        category=product.category or "-",
        content_types=", ".join(CONTENT_TYPES),
    )

    try:
        raw = provider.complete(prompt, json_mode=True)
        ideas_data = extract_json(raw)
    except (AIProviderError, ValueError) as exc:
        raise AIProviderError(f"Failed to generate content ideas: {exc}") from exc

    if isinstance(ideas_data, dict):
        ideas_data = ideas_data.get("ideas", [ideas_data])

    if not isinstance(ideas_data, list) or not ideas_data:
        raise AIProviderError("AI did not return a non-empty list of ideas")

    content = Content(product_id=product.id, status="IDEA")
    db.add(content)
    db.flush()

    best_idea = max(ideas_data, key=_score_idea)

    for idea_data in ideas_data:
        db.add(
            ContentIdea(
                content_id=content.id,
                hook=idea_data.get("hook", ""),
                angle=idea_data.get("angle", ""),
                target_audience=idea_data.get("target_audience", ""),
                content_type=idea_data.get("content_type", "problem_solution"),
                estimated_duration=idea_data.get("estimated_duration", 30),
                ai_provider=provider.name,
                status="selected" if idea_data is best_idea else "generated",
            )
        )

    db.commit()
    db.refresh(content)
    return content
