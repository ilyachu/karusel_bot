from dataclasses import asdict, dataclass, field, replace
import re


THEME_SYSTEMS = {
    "business_dark": {
        "font_style": "standard",
        "eyebrows": {
            "hook": "Главное",
            "context": "Контекст",
            "point": "Суть",
            "proof": "Факт",
            "example": "Пример",
            "checklist": "Шаги",
            "cta": "Итог",
        },
    },
    "minimal_light": {
        "font_style": "prosto",
        "eyebrows": {
            "hook": "Главное",
            "context": "Контекст",
            "point": "Суть",
            "proof": "Факт",
            "example": "Пример",
            "checklist": "Шаги",
            "cta": "Итог",
        },
    },
    "creator_bold": {
        "font_style": "dela",
        "eyebrows": {
            "hook": "Главное",
            "context": "Контекст",
            "point": "Суть",
            "proof": "Факт",
            "example": "Пример",
            "checklist": "Шаги",
            "cta": "Итог",
        },
    },
    "editorial_premium": {
        "font_style": "rampart",
        "eyebrows": {
            "hook": "Главное",
            "context": "Контекст",
            "point": "Суть",
            "proof": "Факт",
            "example": "Пример",
            "checklist": "Шаги",
            "cta": "Итог",
        },
    },
    "memory_archive": {
        "font_style": "standard",
        "eyebrows": {
            "hook": "Главное",
            "context": "Контекст",
            "point": "Суть",
            "proof": "Факт",
            "example": "Пример",
            "checklist": "Шаги",
            "cta": "Итог",
        },
    },
    "founder_brief": {
        "font_style": "prosto",
        "eyebrows": {
            "hook": "Главное",
            "context": "Контекст",
            "point": "Суть",
            "proof": "Факт",
            "example": "Пример",
            "checklist": "Шаги",
            "cta": "Итог",
        },
    },
    "growth_black": {
        "font_style": "dela",
        "eyebrows": {
            "hook": "Главное",
            "context": "Контекст",
            "point": "Суть",
            "proof": "Факт",
            "example": "Пример",
            "checklist": "Шаги",
            "cta": "Итог",
        },
    },
    "research_mono": {
        "font_style": "standard",
        "eyebrows": {
            "hook": "Главное",
            "context": "Контекст",
            "point": "Суть",
            "proof": "Факт",
            "example": "Пример",
            "checklist": "Шаги",
            "cta": "Итог",
        },
    },
}

THEME_LABELS = {
    "auto": "🧠 Auto",
    "memory_archive": "🗂 Memory Archive",
    "founder_brief": "📌 Founder Brief",
    "growth_black": "📈 Growth Black",
    "research_mono": "🔬 Research Mono",
}

THEME_KEYWORDS = {
    "memory_archive": [
        "memory", "mempalace", "памят", "контекст", "chat", "чаты",
        "telegram", "knowledge", "замет", "архив", "документ", "context",
    ],
    "growth_black": [
        "growth", "рост", "revenue", "выруч", "cpa", "cac", "roas", "romi",
        "retention", "конверс", "воронк", "funnel", "marketing", "ads",
        "реклама", "трафик", "sales", "crm", "scale", "performance",
    ],
    "founder_brief": [
        "founder", "фаундер", "startup", "стартап", "product", "продукт",
        "strategy", "стратег", "roadmap", "запуск", "команд", "позиционир",
        "pricing", "gtm", "decision", "решени", "market", "рынок",
    ],
    "research_mono": [
        "research", "исслед", "framework", "фреймворк", "protocol", "протокол",
        "benchmark", "бенчмарк", "architecture", "архитект", "rag", "evaluation",
        "paper", "hypothesis", "гипотез", "method", "метод", "model", "модель",
    ],
}


@dataclass(frozen=True)
class SlidePlanEntry:
    index: int
    role: str
    title: str
    body: str
    emphasis: list[str]
    density: str
    theme_hint: str


@dataclass(frozen=True)
class CarouselPlan:
    goal: str
    audience: str
    tone: str
    theme_hint: str
    cta: str
    slides: list[SlidePlanEntry]


@dataclass(frozen=True)
class LayoutSpec:
    slide_index: int
    total_slides: int
    role: str
    theme: str
    font_style: str
    variant: str
    text_position: str
    badge_text: str
    title: str
    body: str
    highlight_words: list[str]
    density: str
    show_progress: bool
    supporting_cards: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ThemeDecision:
    selected_theme: str
    proposed_theme: str
    scores: dict[str, int]
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def build_instagram_layout_specs(plan: CarouselPlan) -> list[LayoutSpec]:
    theme = plan.theme_hint if plan.theme_hint in THEME_SYSTEMS else "business_dark"
    theme_system = THEME_SYSTEMS[theme]
    total_slides = len(plan.slides)

    specs: list[LayoutSpec] = []
    for slide in plan.slides:
        variant = _choose_variant(slide.role, slide.density, slide.index, total_slides)
        text_position = _choose_text_position(variant, slide.role)
        specs.append(
            LayoutSpec(
                slide_index=slide.index,
                total_slides=total_slides,
                role=slide.role,
                theme=theme,
                font_style=theme_system["font_style"],
                variant=variant,
                text_position=text_position,
                badge_text="",
                title=slide.title,
                body=slide.body,
                highlight_words=slide.emphasis,
                density=slide.density,
                show_progress=total_slides > 1,
                supporting_cards=[],
            )
        )
    return specs


def apply_theme_override(plan: CarouselPlan, theme_name: str) -> tuple[CarouselPlan, ThemeDecision]:
    selected = theme_name if theme_name in THEME_SYSTEMS else plan.theme_hint
    updated_plan = replace(
        plan,
        theme_hint=selected,
        slides=[replace(slide, theme_hint=selected) for slide in plan.slides],
    )
    return updated_plan, ThemeDecision(
        selected_theme=selected,
        proposed_theme=plan.theme_hint,
        scores={},
        reason=f"Theme lock forced `{selected}`.",
    )


def apply_theme_selection_policy(plan: CarouselPlan, source_text: str) -> tuple[CarouselPlan, ThemeDecision]:
    scores = _score_themes(source_text, plan)
    proposed = plan.theme_hint if plan.theme_hint in THEME_SYSTEMS else "business_dark"
    auto_allowed = {
        "business_dark",
        "minimal_light",
        "editorial_premium",
        "memory_archive",
        "founder_brief",
        "growth_black",
        "research_mono",
    }
    scores.pop("creator_bold", None)
    if proposed in scores and proposed in auto_allowed:
        scores[proposed] += 2

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    selected, top_score = ranked[0]
    runner_up_score = ranked[1][1] if len(ranked) > 1 else -1

    if top_score < 2:
        selected = proposed if proposed in auto_allowed else "business_dark"
        reason = "No strong lexical signal detected; using proposed/default theme."
    elif top_score == runner_up_score and proposed in auto_allowed:
        selected = proposed
        reason = "Theme scores tied; keeping the model-proposed theme."
    else:
        reason = f"Theme policy selected `{selected}` from lexical/content signals."

    updated_plan = replace(
        plan,
        theme_hint=selected,
        slides=[replace(slide, theme_hint=selected) for slide in plan.slides],
    )
    return updated_plan, ThemeDecision(
        selected_theme=selected,
        proposed_theme=proposed,
        scores=scores,
        reason=reason,
    )


def parse_carousel_plan(raw_plan: dict) -> CarouselPlan:
    slides: list[SlidePlanEntry] = []
    for idx, slide in enumerate(raw_plan.get("slides", []), start=1):
        slides.append(
            SlidePlanEntry(
                index=int(slide.get("index", idx)),
                role=str(slide.get("role", "point")),
                title=str(slide.get("title", "")).strip(),
                body=str(slide.get("body", "")).strip(),
                emphasis=_normalize_list(slide.get("emphasis")),
                density=str(slide.get("density", "medium")),
                theme_hint=str(slide.get("theme_hint", raw_plan.get("carousel", {}).get("theme_hint", "business_dark"))),
            )
        )

    carousel = raw_plan.get("carousel", {})
    return CarouselPlan(
        goal=str(carousel.get("goal", "instagram_carousel")),
        audience=str(carousel.get("audience", "creators")),
        tone=str(carousel.get("tone", "clear_confident")),
        theme_hint=str(carousel.get("theme_hint", "business_dark")),
        cta=str(carousel.get("cta", "save_and_follow")),
        slides=slides,
    )


def build_fallback_instagram_plan(slides_content: list[dict], theme_hint: str = "business_dark") -> CarouselPlan:
    slides: list[SlidePlanEntry] = []
    total = len(slides_content)
    for idx, slide in enumerate(slides_content, start=1):
        if idx == 1:
            role = "hook"
        elif idx == total:
            role = "cta"
        elif idx == 2:
            role = "context"
        else:
            role = "point"

        body = str(slide.get("body", "")).strip()
        title = str(slide.get("title", "")).strip()
        density = "high" if len(body) > 190 else "medium" if len(body) > 110 else "low"
        emphasis = [title.split(":")[0][:28]] if title else []

        slides.append(
            SlidePlanEntry(
                index=idx,
                role=role,
                title=title,
                body=body,
                emphasis=emphasis,
                density=density,
                theme_hint=theme_hint,
            )
        )

    return CarouselPlan(
        goal="instagram_carousel",
        audience="creators",
        tone="clear_confident",
        theme_hint=theme_hint,
        cta="save_and_follow",
        slides=slides,
    )


def _choose_variant(role: str, density: str, index: int, total_slides: int) -> str:
    if role == "hook" or index == 1:
        return "cover"
    if role == "cta" or index == total_slides:
        return "closing"
    if role == "proof":
        return "stat_focus"
    if role == "checklist":
        return "checklist"
    if density == "low":
        return "spotlight"
    return "editorial"


def _choose_text_position(variant: str, role: str) -> str:
    if variant in {"cover", "closing", "stat_focus"}:
        return "center"
    if role in {"context", "checklist"}:
        return "top"
    return "center"


def _normalize_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _extract_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [_trim_text(part.strip(), 60) for part in parts if part.strip()]


def _extract_phrases(text: str, limit: int) -> list[str]:
    parts = re.split(r"[,;]\s+|(?<=[.!?])\s+", text.strip())
    return [_trim_text(part.strip(), 44) for part in parts if part.strip()][:limit]


def _trim_text(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _score_themes(source_text: str, plan: CarouselPlan) -> dict[str, int]:
    corpus = " ".join(
        [
            source_text,
            plan.goal,
            plan.audience,
            plan.tone,
            plan.cta,
            " ".join(slide.title for slide in plan.slides),
            " ".join(slide.body for slide in plan.slides),
        ]
    ).lower()

    scores = {theme: 0 for theme in THEME_SYSTEMS.keys()}
    for theme, keywords in THEME_KEYWORDS.items():
        for keyword in keywords:
            if keyword in corpus:
                scores[theme] += 2 if len(keyword) > 6 else 1

    if any(slide.role == "proof" for slide in plan.slides):
        scores["research_mono"] += 1
        scores["growth_black"] += 1
    if any(slide.role == "cta" for slide in plan.slides):
        scores["founder_brief"] += 1
    if any("telegram" in slide.body.lower() or "github" in slide.body.lower() for slide in plan.slides):
        scores["research_mono"] += 1
    return scores
