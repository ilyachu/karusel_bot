from dataclasses import asdict, dataclass, field
import re


THEME_SYSTEMS = {
    "business_dark": {
        "font_style": "standard",
        "eyebrows": {
            "hook": "Hook",
            "context": "Context",
            "point": "Key point",
            "proof": "Proof",
            "example": "Example",
            "checklist": "Checklist",
            "cta": "CTA",
        },
    },
    "minimal_light": {
        "font_style": "prosto",
        "eyebrows": {
            "hook": "Idea",
            "context": "Why it matters",
            "point": "Point",
            "proof": "Result",
            "example": "Example",
            "checklist": "Steps",
            "cta": "Next step",
        },
    },
    "creator_bold": {
        "font_style": "dela",
        "eyebrows": {
            "hook": "Swipe",
            "context": "Story",
            "point": "Move",
            "proof": "Result",
            "example": "Case",
            "checklist": "Checklist",
            "cta": "Follow",
        },
    },
    "editorial_premium": {
        "font_style": "rampart",
        "eyebrows": {
            "hook": "Cover",
            "context": "Thesis",
            "point": "Argument",
            "proof": "Signal",
            "example": "Case",
            "checklist": "Framework",
            "cta": "Close",
        },
    },
    "memory_archive": {
        "font_style": "standard",
        "eyebrows": {
            "hook": "Memory",
            "context": "Pressure",
            "point": "Signal",
            "proof": "System",
            "example": "Test",
            "checklist": "Notes",
            "cta": "Save",
        },
    },
    "founder_brief": {
        "font_style": "prosto",
        "eyebrows": {
            "hook": "Brief",
            "context": "Context",
            "point": "Move",
            "proof": "Metric",
            "example": "Case",
            "checklist": "Plan",
            "cta": "Next",
        },
    },
    "growth_black": {
        "font_style": "dela",
        "eyebrows": {
            "hook": "Growth",
            "context": "Constraint",
            "point": "Lever",
            "proof": "Signal",
            "example": "Play",
            "checklist": "Ops",
            "cta": "Action",
        },
    },
    "research_mono": {
        "font_style": "standard",
        "eyebrows": {
            "hook": "Research",
            "context": "Frame",
            "point": "Finding",
            "proof": "Evidence",
            "example": "Example",
            "checklist": "Protocol",
            "cta": "Keep",
        },
    },
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
                badge_text=theme_system["eyebrows"].get(slide.role, "Slide"),
                title=slide.title,
                body=slide.body,
                highlight_words=slide.emphasis,
                density=slide.density,
                show_progress=total_slides > 1,
                supporting_cards=_build_supporting_cards(slide.role, slide.title, slide.body, slide.emphasis, slide.density),
            )
        )
    return specs


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


def _build_supporting_cards(role: str, title: str, body: str, emphasis: list[str], density: str) -> list[dict]:
    sentences = _extract_sentences(body)
    cards: list[dict] = []

    if role == "hook":
        cards.append({"label": "Core", "text": emphasis[0] if emphasis else title})
        if sentences:
            cards.append({"label": "Tension", "text": sentences[0]})
    elif role == "context":
        cards.append({"label": "Why now", "text": sentences[0] if sentences else body})
        if len(sentences) > 1:
            cards.append({"label": "Pressure", "text": sentences[1]})
    elif role == "proof":
        cards.append({"label": "Signal", "text": emphasis[0] if emphasis else title})
        if sentences:
            cards.append({"label": "Evidence", "text": sentences[0]})
    elif role == "example":
        cards.append({"label": "Case", "text": title})
        if sentences:
            cards.append({"label": "Observed", "text": sentences[0]})
    elif role == "checklist":
        chunks = _extract_phrases(body, limit=3)
        for idx, chunk in enumerate(chunks, start=1):
            cards.append({"label": f"Step {idx}", "text": chunk})
    elif role == "cta":
        cards.append({"label": "Next", "text": sentences[0] if sentences else body})
    else:
        cards.append({"label": "Key", "text": emphasis[0] if emphasis else title})
        if density in {"medium", "high"} and sentences:
            cards.append({"label": "Angle", "text": sentences[0]})
        if density == "high" and len(sentences) > 1:
            cards.append({"label": "Detail", "text": sentences[1]})

    deduped: list[dict] = []
    seen = set()
    for card in cards:
        text = _trim_text(card["text"], 52)
        if not text:
            continue
        key = (card["label"], text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"label": card["label"], "text": text})
    return deduped[:3]


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
