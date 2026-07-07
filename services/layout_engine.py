from dataclasses import asdict, dataclass, field, replace
import re

DEFAULT_CTA_TITLE = "Подписывайтесь на канал"
DEFAULT_CTA_BODY = "Подписывайтесь на канал в шапке профиля чтоб получать больше информации"
EDITORIAL_CTA_TITLE = "Сохрани карусель"
EDITORIAL_CTA_BODY = "Вернись к разбору позже или забери идею для своей системы."


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

VISUAL_MODE_LABELS = {
    "auto": "Auto",
    "classic": "Classic",
    "editorial": "Editorial",
    "brief": "Founder Brief",
    "data": "Data Brief",
}

PRESET_VISUAL_PROFILES = {
    "glitch": {
        "theme": "research_mono",
        "visual_mode": "data",
        "label": "Glitch Data",
    },
    "lofi": {
        "theme": "memory_archive",
        "visual_mode": "editorial",
        "label": "Lofi Editorial",
    },
    "neon": {
        "theme": "growth_black",
        "visual_mode": "data",
        "label": "Neon Data",
    },
    "paper": {
        "theme": "founder_brief",
        "visual_mode": "brief",
        "label": "Paper Brief",
    },
    "acid": {
        "theme": "growth_black",
        "visual_mode": "editorial",
        "label": "Acid Editorial",
    },
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
    supporting_cards: list[dict] = field(default_factory=list)
    html_body: str = ""
    archetype: str = ""


@dataclass(frozen=True)
class CarouselPlan:
    goal: str
    audience: str
    tone: str
    theme_hint: str
    cta: str
    slides: list[SlidePlanEntry]
    layout_style: str = "magazine"


LAYOUT_STYLE_LABELS = {
    "magazine": "Журнал",
    "terminal": "Терминал",
    "poster": "Плакат",
    "carddeck": "Карточки",
}

LAYOUT_STYLE_DESCRIPTIONS = {
    "magazine": "Серьёзный журнальный стиль с засечками. Для разборов, аналитики, эссе.",
    "terminal": "Хакерский моноширинный стиль. Для технических обзоров, бенчмарков, AI-новостей.",
    "poster": "Яркий плакатный стиль. Для манифестов, анонсов, сильных утверждений.",
    "carddeck": "Чистый карточный стиль. Для списков, чеклистов, образовательного контента.",
}

SLIDE_ARCHETYPES = {
    "hero_center",
    "split_story",
    "checklist_stack",
    "stat_panel",
    "quote_poster",
    "timeline_steps",
    "comparison_grid",
    "soft_cta",
}

LAYOUT_STYLE_FONTS = {
    "magazine": {
        "heading": "'Cormorant Garamond', Georgia, 'Times New Roman', serif",
        "body": "'Manrope', system-ui, -apple-system, sans-serif",
        "google": "Cormorant+Garamond:wght@400;500;600;700|Manrope:wght@400;500;600;700;800",
    },
    "terminal": {
        "heading": "'JetBrains Mono', 'SFMono-Regular', 'Menlo', monospace",
        "body": "'JetBrains Mono', 'SFMono-Regular', 'Menlo', monospace",
        "google": "JetBrains+Mono:wght@400;500;700;800",
    },
    "poster": {
        "heading": "'Sora', 'Space Grotesk', 'Arial Black', sans-serif",
        "body": "'Manrope', system-ui, -apple-system, sans-serif",
        "google": "Sora:wght@400;600;700;800|Manrope:wght@400;500;600;700;800",
    },
    "carddeck": {
        "heading": "'Manrope', system-ui, -apple-system, sans-serif",
        "body": "'Manrope', system-ui, -apple-system, sans-serif",
        "google": "Manrope:wght@400;500;600;700;800",
    },
}


@dataclass(frozen=True)
class LayoutSpec:
    slide_index: int
    total_slides: int
    role: str
    theme: str
    visual_mode: str
    font_style: str
    variant: str
    text_position: str
    badge_text: str
    title: str
    body: str
    highlight_words: list[str]
    density: str
    show_progress: bool
    layout_style: str = "magazine"
    section_label: str = ""
    section_number: str = ""
    watermark_number: str = ""
    footer_tags: list[str] = field(default_factory=list)
    accent_spans: list[str] = field(default_factory=list)
    brand_mark: str = ""
    progress_style: str = "pill"
    supporting_cards: list[dict] = field(default_factory=list)
    html_body: str = ""
    archetype: str = ""

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


@dataclass(frozen=True)
class VisualModeDecision:
    requested_mode: str
    resolved_mode: str
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def build_instagram_layout_specs(plan: CarouselPlan, visual_mode: str = "classic", layout_style: str = "magazine") -> list[LayoutSpec]:
    if layout_style not in LAYOUT_STYLE_LABELS:
        layout_style = "magazine"
    decision = resolve_visual_mode(plan, visual_mode)
    if decision.resolved_mode == "editorial":
        return _build_editorial_layout_specs(plan, layout_style=layout_style)
    if decision.resolved_mode == "brief":
        return _build_brief_layout_specs(plan, layout_style=layout_style)
    if decision.resolved_mode == "data":
        return _build_data_layout_specs(plan, layout_style=layout_style)
    return _build_classic_layout_specs(plan, layout_style=layout_style)


def resolve_preset_visual_profile(preset_key: str) -> dict[str, str]:
    return PRESET_VISUAL_PROFILES.get(preset_key, PRESET_VISUAL_PROFILES["lofi"])


def resolve_visual_mode(plan: CarouselPlan, visual_mode: str = "classic") -> VisualModeDecision:
    requested = visual_mode if visual_mode in VISUAL_MODE_LABELS else "classic"
    if requested != "auto":
        return VisualModeDecision(
            requested_mode=requested,
            resolved_mode=requested,
            reason=f"{VISUAL_MODE_LABELS[requested]} selected manually.",
        )

    corpus = _plan_corpus(plan)
    number_count = len(_meaningful_number_matches(corpus))
    data_terms = _count_matches(
        corpus,
        [
            "api", "benchmark", "model", "модель", "модели", "openai", "nvidia",
            "deepseek", "base url", "token", "токен", "вычислен", "research",
            "исслед", "метрик", "метрика",
        ],
    )
    brief_terms = _count_matches(
        corpus,
        [
            "founder", "фаундер", "product", "продукт", "strategy", "стратег",
            "roadmap", "pricing", "gtm", "market", "рынок", "startup", "стартап",
            "decision", "решени", "launch", "запуск",
        ],
    )
    narrative_terms = _count_matches(
        corpus,
        ["история", "новость", "почему", "контекст", "разбор", "сценарий", "case", "кейс"],
    )

    if number_count >= 2 or (number_count >= 1 and data_terms >= 1) or data_terms >= 3:
        return VisualModeDecision(
            requested_mode="auto",
            resolved_mode="data",
            reason=f"Data Brief: found {number_count} numeric signal(s) and {data_terms} data/API signal(s).",
        )
    if plan.theme_hint == "founder_brief" or brief_terms >= 2:
        return VisualModeDecision(
            requested_mode="auto",
            resolved_mode="brief",
            reason=f"Founder Brief: found {brief_terms} product/founder signal(s).",
        )
    return VisualModeDecision(
        requested_mode="auto",
        resolved_mode="editorial",
        reason=f"Editorial: narrative/news structure detected ({narrative_terms} narrative signal(s)).",
    )


def _build_classic_layout_specs(plan: CarouselPlan, layout_style: str = "magazine") -> list[LayoutSpec]:
    theme = plan.theme_hint if plan.theme_hint in THEME_SYSTEMS else "business_dark"
    theme_system = THEME_SYSTEMS[theme]
    total_slides = len(plan.slides)

    specs: list[LayoutSpec] = []
    for slide in plan.slides:
        variant = _choose_variant(slide.role, slide.density, slide.index, total_slides)
        text_position = _choose_text_position(variant, slide.role)
        badge_text = theme_system["eyebrows"].get(slide.role, "Суть")
        supporting_cards = _resolve_supporting_cards(slide, variant)
        specs.append(
            LayoutSpec(
                slide_index=slide.index,
                total_slides=total_slides,
                role=slide.role,
                theme=theme,
                visual_mode="classic",
                font_style=theme_system["font_style"],
                variant=variant,
                text_position=text_position,
                badge_text=badge_text,
                title=slide.title,
                body=slide.body,
                highlight_words=slide.emphasis,
                density=slide.density,
                show_progress=total_slides > 1,
                layout_style=layout_style,
                supporting_cards=supporting_cards,
                html_body=slide.html_body,
                archetype=slide.archetype or _infer_archetype(slide.role, variant),
            )
        )
    return specs


def _build_editorial_layout_specs(plan: CarouselPlan, layout_style: str = "magazine") -> list[LayoutSpec]:
    theme = plan.theme_hint if plan.theme_hint in THEME_SYSTEMS else "business_dark"
    theme_system = THEME_SYSTEMS[theme]
    total_slides = len(plan.slides)

    specs: list[LayoutSpec] = []
    for slide in plan.slides:
        variant = _choose_editorial_variant(slide, total_slides)
        specs.append(
            LayoutSpec(
                slide_index=slide.index,
                total_slides=total_slides,
                role=slide.role,
                theme=theme,
                visual_mode="editorial",
                font_style=theme_system["font_style"],
                variant=variant,
                text_position="top",
                badge_text=theme_system["eyebrows"].get(slide.role, "Суть"),
                title=slide.title,
                body=slide.body,
                highlight_words=slide.emphasis,
                density=slide.density,
                show_progress=total_slides > 1,
                layout_style=layout_style,
                section_label=_editorial_section_label(slide, variant),
                section_number=f"{slide.index:02d}",
                watermark_number=f"{slide.index:02d}",
                footer_tags=_build_editorial_tags(slide),
                accent_spans=slide.emphasis or _infer_editorial_accent_spans(slide),
                brand_mark="",
                progress_style="line",
                supporting_cards=_build_editorial_supporting_cards(slide, variant),
                html_body=slide.html_body,
                archetype=slide.archetype or _infer_archetype(slide.role, variant),
            )
        )
    return specs


def _build_brief_layout_specs(plan: CarouselPlan, layout_style: str = "magazine") -> list[LayoutSpec]:
    theme = plan.theme_hint if plan.theme_hint in THEME_SYSTEMS else "founder_brief"
    theme_system = THEME_SYSTEMS[theme]
    total_slides = len(plan.slides)

    specs: list[LayoutSpec] = []
    for slide in plan.slides:
        variant = _choose_brief_variant(slide, total_slides)
        specs.append(
            LayoutSpec(
                slide_index=slide.index,
                total_slides=total_slides,
                role=slide.role,
                theme=theme,
                visual_mode="brief",
                font_style=theme_system["font_style"],
                variant=variant,
                text_position="top",
                badge_text=theme_system["eyebrows"].get(slide.role, "Суть"),
                title=slide.title,
                body=slide.body,
                highlight_words=slide.emphasis,
                density=slide.density,
                show_progress=total_slides > 1,
                layout_style=layout_style,
                section_label=_brief_section_label(slide, variant),
                section_number=f"{slide.index:02d}",
                watermark_number=f"{slide.index:02d}",
                footer_tags=_build_editorial_tags(slide),
                accent_spans=slide.emphasis or _infer_editorial_accent_spans(slide),
                progress_style="line",
                supporting_cards=_build_brief_supporting_cards(slide, variant),
                html_body=slide.html_body,
                archetype=slide.archetype or _infer_archetype(slide.role, variant),
            )
        )
    return specs


def _build_data_layout_specs(plan: CarouselPlan, layout_style: str = "magazine") -> list[LayoutSpec]:
    theme = plan.theme_hint if plan.theme_hint in THEME_SYSTEMS else "research_mono"
    theme_system = THEME_SYSTEMS[theme]
    total_slides = len(plan.slides)

    specs: list[LayoutSpec] = []
    for slide in plan.slides:
        variant = _choose_data_variant(slide, total_slides)
        stat = _extract_stat_token(" ".join([slide.title, slide.body]))
        supporting_cards = _build_data_supporting_cards(slide, variant, stat)
        specs.append(
            LayoutSpec(
                slide_index=slide.index,
                total_slides=total_slides,
                role=slide.role,
                theme=theme,
                visual_mode="data",
                font_style=theme_system["font_style"],
                variant=variant,
                text_position="top",
                badge_text=theme_system["eyebrows"].get(slide.role, "Факт"),
                title=slide.title,
                body=slide.body,
                highlight_words=slide.emphasis,
                density=slide.density,
                show_progress=total_slides > 1,
                layout_style=layout_style,
                section_label=_data_section_label(slide, variant),
                section_number=f"{slide.index:02d}",
                watermark_number=stat or f"{slide.index:02d}",
                footer_tags=_build_editorial_tags(slide),
                accent_spans=slide.emphasis or ([stat] if stat else _infer_editorial_accent_spans(slide)),
                progress_style="line",
                supporting_cards=supporting_cards,
                html_body=slide.html_body,
                archetype=slide.archetype or _infer_archetype(slide.role, variant),
            )
        )
    return specs


def enforce_default_cta_slide(plan: CarouselPlan, visual_mode: str = "classic") -> CarouselPlan:
    if not plan.slides:
        return plan

    resolved_mode = resolve_visual_mode(plan, visual_mode).resolved_mode
    title = DEFAULT_CTA_TITLE if resolved_mode == "classic" else EDITORIAL_CTA_TITLE
    body = DEFAULT_CTA_BODY if resolved_mode == "classic" else EDITORIAL_CTA_BODY
    last_index = len(plan.slides)
    updated_last = replace(
        plan.slides[-1],
        index=last_index,
        role="cta",
        title=title,
        body=body,
        emphasis=[],
        density="low",
    )
    updated_slides = list(plan.slides[:-1]) + [updated_last]
    return replace(plan, slides=updated_slides, cta="follow_profile")


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
                supporting_cards=_normalize_supporting_cards(slide.get("supporting_cards")),
                html_body=str(slide.get("html_body", "")).strip(),
                archetype=_normalize_archetype(str(slide.get("archetype", ""))),
            )
        )

    carousel = raw_plan.get("carousel", {})
    return CarouselPlan(
        goal=str(carousel.get("goal", "instagram_carousel")),
        audience=str(carousel.get("audience", "creators")),
        tone=str(carousel.get("tone", "clear_confident")),
        theme_hint=str(carousel.get("theme_hint", "business_dark")),
        cta=str(carousel.get("cta", "save_and_follow")),
        layout_style=str(carousel.get("layout_style", "magazine")),
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
                supporting_cards=_normalize_supporting_cards(slide.get("supporting_cards")),
                html_body=str(slide.get("html_body", "")).strip(),
                archetype=_normalize_archetype(str(slide.get("archetype", ""))),
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
    if role == "context" and density in {"medium", "high"}:
        return "framework_grid"
    if role == "proof":
        return "stat_focus"
    if role == "checklist":
        return "checklist"
    if role in {"point", "example"} and density == "low":
        return "quote"
    if density == "low":
        return "spotlight"
    return "editorial"


def _normalize_archetype(value: str) -> str:
    normalized = (value or "").strip()
    if normalized in SLIDE_ARCHETYPES:
        return normalized
    return ""


def _infer_archetype(role: str, variant: str) -> str:
    if role == "hook":
        return "hero_center"
    if role == "cta":
        return "soft_cta"
    if role == "checklist":
        return "checklist_stack"
    if role == "proof" or variant in {"stat_focus", "data_stat", "editorial_stat"}:
        return "stat_panel"
    if role == "example":
        return "comparison_grid"
    if role == "context":
        return "split_story"
    if variant in {"quote", "spotlight"}:
        return "quote_poster"
    return "timeline_steps"


def _choose_editorial_variant(slide: SlidePlanEntry, total_slides: int) -> str:
    if slide.index == 1:
        return "editorial_cover"
    if slide.index == total_slides:
        return "editorial_soft_cta"
    stat_signal = bool(_meaningful_number_matches(" ".join([slide.title or "", slide.body or ""])))
    if stat_signal:
        return "editorial_stat"
    if slide.role in {"context", "checklist"}:
        return "editorial_scenario"
    return "editorial_story"


def _choose_brief_variant(slide: SlidePlanEntry, total_slides: int) -> str:
    if slide.index == 1:
        return "brief_cover"
    if slide.index == total_slides or slide.role == "cta":
        return "brief_cta"
    if slide.role in {"context", "checklist"}:
        return "brief_decision"
    return "brief_insight"


def _choose_data_variant(slide: SlidePlanEntry, total_slides: int) -> str:
    if slide.index == 1:
        return "data_cover"
    if slide.index == total_slides or slide.role == "cta":
        return "data_cta"
    if _extract_stat_token(" ".join([slide.title, slide.body])):
        return "data_stat"
    if slide.role in {"context", "checklist"}:
        return "data_protocol"
    return "data_insight"


def _choose_text_position(variant: str, role: str) -> str:
    if variant in {"cover", "closing", "stat_focus", "quote"}:
        return "center"
    if role in {"context", "checklist"} or variant == "framework_grid":
        return "top"
    return "center"


def _resolve_supporting_cards(slide: SlidePlanEntry, variant: str) -> list[dict]:
    """Prefer LLM supporting_cards when they are required for the archetype."""

    llm_cards = _normalize_supporting_cards(slide.supporting_cards)
    archetype = slide.archetype or _infer_archetype(slide.role, variant)
    if archetype == "comparison_grid" and len(llm_cards) >= 2:
        return llm_cards
    heuristic_cards = _build_supporting_cards(slide.body, variant)
    if heuristic_cards:
        return heuristic_cards
    return llm_cards


def _build_supporting_cards(body: str, variant: str) -> list[dict]:
    if variant == "checklist":
        return [{"title": phrase} for phrase in _extract_phrases(body, 3)]
    return []


def _editorial_section_label(slide: SlidePlanEntry, variant: str) -> str:
    if variant == "editorial_cover":
        return "INTRO"
    if variant == "editorial_stat":
        return "ЧТО ЭТО"
    if variant == "editorial_soft_cta":
        return "ФИНАЛ"
    mapping = {
        "context": "СЦЕНАРИЙ",
        "proof": "ФАКТ",
        "example": "КЕЙС",
        "checklist": "СЛОИ",
        "point": "ТЕЗИС",
        "cta": "ФИНАЛ",
    }
    return mapping.get(slide.role, "СЦЕНАРИЙ")


def _brief_section_label(slide: SlidePlanEntry, variant: str) -> str:
    if variant == "brief_cover":
        return "MEMO"
    if variant == "brief_cta":
        return "NEXT"
    mapping = {
        "context": "CONTEXT",
        "proof": "EVIDENCE",
        "example": "CASE",
        "checklist": "OPERATING",
        "point": "DECISION",
    }
    return mapping.get(slide.role, "INSIGHT")


def _data_section_label(slide: SlidePlanEntry, variant: str) -> str:
    if variant == "data_cover":
        return "SIGNAL"
    if variant == "data_stat":
        return "METRIC"
    if variant == "data_cta":
        return "SAVE"
    if variant == "data_protocol":
        return "METHOD"
    return "DETAIL"


def _build_editorial_supporting_cards(slide: SlidePlanEntry, variant: str) -> list[dict]:
    cards = _validated_llm_supporting_cards(slide)
    if cards:
        return cards
    if variant == "editorial_stat":
        stat = _extract_stat_token(" ".join([slide.title, slide.body]))
        return [{"title": stat or "Факт", "body": "ключевой факт"}]
    if variant == "editorial_cover":
        return []
    return []


def _build_brief_supporting_cards(slide: SlidePlanEntry, variant: str) -> list[dict]:
    return _validated_llm_supporting_cards(slide)


def _build_data_supporting_cards(slide: SlidePlanEntry, variant: str, stat: str) -> list[dict]:
    cards = _validated_llm_supporting_cards(slide)
    if cards:
        return cards
    if variant == "data_stat":
        return [
            {"title": stat or "metric", "body": "ключевой показатель"},
        ]
    return []


def _build_editorial_tags(slide: SlidePlanEntry) -> list[str]:
    source = " ".join(part for part in (slide.title or "", slide.body or "") if part).strip()
    priority_matches: list[str] = []
    priority_patterns = [
        r"\bapi key\b",
        r"\bbase url\b",
        r"\bemail\b",
        r"\botp\b",
        r"\bcursor\b",
        r"\bzed\b",
        r"\bopencode\b",
        r"\bhermes\b",
        r"\bopenclaw\b",
        r"\bnvidia\b",
        r"\bdeepseek\b",
        r"\bbuild\.nvidia\.com\b",
        r"\bopenai-compatible\b",
        r"вычислен\w+",
        r"лидер\w+",
    ]
    lowered = source.lower()
    for pattern in priority_patterns:
        match = re.search(pattern, lowered)
        if match:
            value = match.group(0)
            if value not in priority_matches:
                priority_matches.append(value)
        if len(priority_matches) == 4:
            return priority_matches

    stopwords = {
        "и", "а", "но", "для", "через", "после", "в", "на", "по", "из", "не", "это",
        "как", "что", "или", "без", "под", "над", "при", "от", "до", "уже", "просто",
        "который", "которая", "которые", "рынка", "разбираем", "меняете", "только",
        "достаточно", "указать", "вставить", "выбрать", "можно", "модели", "модель",
        "здесь", "открытая", "закрытые",
    }
    tokens = re.findall(r"[A-Za-zА-Яа-я0-9.+-]{3,}", source)
    tags: list[str] = []
    for token in tokens:
        normalized = token.lower().strip(".")
        if normalized in stopwords:
            continue
        if normalized.isdigit():
            continue
        if re.fullmatch(r"v\d+(?:\.\d+)?", normalized):
            continue
        if len(normalized) > 18:
            continue
        if normalized not in tags and normalized not in priority_matches:
            tags.append(normalized)
        if len(priority_matches) + len(tags) >= 4:
            break
    merged = priority_matches + [tag for tag in tags if tag not in priority_matches]
    return (merged[:4]) or [slide.role.lower()]


def _infer_editorial_accent_spans(slide: SlidePlanEntry) -> list[str]:
    for source in (slide.title, slide.body):
        parts = [part.strip() for part in re.split(r"[,.\n]", source or "") if part.strip()]
        for part in parts:
            if 6 <= len(part) <= 42:
                return [part]
    return []


def _normalize_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _normalize_supporting_cards(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    cards: list[dict] = []
    for item in value[:3]:
        if not isinstance(item, dict):
            continue
        title = _trim_text(str(item.get("title") or item.get("label") or "").strip(), 18)
        body = _trim_text(str(item.get("body") or item.get("value") or "").strip(), 54)
        if title and body:
            cards.append({"title": title, "body": body})
    return cards


def _validated_llm_supporting_cards(slide: SlidePlanEntry) -> list[dict]:
    cards: list[dict] = []
    source_title = _normalize_for_overlap(slide.title)
    source_body = _normalize_for_overlap(slide.body)
    for card in slide.supporting_cards[:3]:
        title = _trim_text(str(card.get("title", "")).strip(), 18)
        body = _trim_text(str(card.get("body", "")).strip(), 54)
        if not title or not body:
            continue
        if "…" in title or "…" in body:
            continue
        normalized_body = _normalize_for_overlap(body)
        if not normalized_body:
            continue
        if normalized_body in source_title or normalized_body in source_body:
            continue
        if _overlap_ratio(normalized_body, source_body) > 0.72:
            continue
        cards.append({"title": title, "body": body})
    return cards


def _normalize_for_overlap(text: str) -> str:
    text = re.sub(r"[^A-Za-zА-Яа-я0-9 ]+", " ", (text or "").lower())
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _overlap_ratio(short_text: str, long_text: str) -> float:
    short_words = {word for word in short_text.split() if len(word) > 2}
    long_words = {word for word in long_text.split() if len(word) > 2}
    if not short_words or not long_words:
        return 0.0
    return len(short_words & long_words) / len(short_words)


def _extract_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [_trim_text(part.strip(), 60) for part in parts if part.strip()]


def _extract_phrases(text: str, limit: int) -> list[str]:
    parts = re.split(r"[,;]\s+|(?<=[.!?])\s+", text.strip())
    return [_trim_text(part.strip(), 44) for part in parts if part.strip()][:limit]


def _extract_stat_token(text: str) -> str:
    matches = _meaningful_number_matches(text)
    if not matches:
        return ""
    return matches[0].strip()


def _meaningful_number_matches(text: str) -> list[str]:
    cleaned = re.sub(r"https?://\S+", " ", text or "")
    cleaned = re.sub(r"\b[a-z]{1,8}/v\d+(?:\.\d+)?\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bv\d+(?:\.\d+)?\b", " ", cleaned, flags=re.IGNORECASE)
    pattern = re.compile(
        r"(?<![\w/])\d{2,}(?:[.,]\d+)?(?:\s?(?:тыс(?:яч)?|млн|млрд|%|x|к|k|m|b))?(?![\w/])",
        re.IGNORECASE,
    )
    return [match.group(0) for match in pattern.finditer(cleaned)]


def _plan_corpus(plan: CarouselPlan) -> str:
    return " ".join(
        [
            plan.goal,
            plan.audience,
            plan.tone,
            plan.cta,
            plan.theme_hint,
            " ".join(slide.role for slide in plan.slides),
            " ".join(slide.title for slide in plan.slides),
            " ".join(slide.body for slide in plan.slides),
        ]
    ).lower()


def _count_matches(corpus: str, needles: list[str]) -> int:
    return sum(1 for needle in needles if needle in corpus)


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
