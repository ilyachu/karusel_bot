from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from services.cover_renderer import image_bytes_to_data_url


BACKGROUND_DIR = Path(__file__).resolve().parents[1] / "assets" / "background_presets"


@dataclass(frozen=True)
class BackgroundPreset:
    preset_id: str
    filename: str
    family: str
    brightness: str
    contrast: str
    fit_styles: tuple[str, ...]
    fit_themes: tuple[str, ...]
    fit_archetypes: tuple[str, ...]

    @property
    def path(self) -> Path:
        return BACKGROUND_DIR / self.filename


BACKGROUND_PRESETS: tuple[BackgroundPreset, ...] = (
    BackgroundPreset("soft_red_spray", "bg_01.jpeg", "soft_glow", "light", "medium", ("magazine", "carddeck", "poster"), ("minimal_light", "founder_brief", "creator_bold"), ("hero_center", "soft_cta", "quote_poster")),
    BackgroundPreset("blue_aura", "bg_02.jpeg", "soft_glow", "light", "low", ("magazine", "carddeck"), ("minimal_light", "founder_brief", "memory_archive"), ("hero_center", "split_story", "soft_cta")),
    BackgroundPreset("blue_foil", "bg_03.jpeg", "foil", "light", "high", ("terminal", "poster"), ("research_mono", "growth_black", "creator_bold"), ("stat_panel", "comparison_grid", "quote_poster")),
    BackgroundPreset("pink_foil", "bg_04.jpeg", "foil", "light", "high", ("poster", "carddeck"), ("creator_bold", "editorial_premium"), ("hero_center", "quote_poster", "soft_cta")),
    BackgroundPreset("cloud_canvas", "bg_05.jpeg", "paper", "light", "low", ("magazine", "carddeck"), ("minimal_light", "founder_brief", "memory_archive"), ("split_story", "timeline_steps", "soft_cta")),
    BackgroundPreset("acid_swirl", "bg_06.jpeg", "bold", "light", "high", ("poster",), ("creator_bold", "editorial_premium"), ("hero_center", "quote_poster")),
    BackgroundPreset("pastel_sun", "bg_07.jpeg", "soft_glow", "light", "medium", ("magazine", "carddeck"), ("memory_archive", "founder_brief", "minimal_light"), ("hero_center", "soft_cta", "split_story")),
    BackgroundPreset("soft_blue_blur", "bg_08.jpeg", "soft_glow", "light", "low", ("magazine", "carddeck"), ("minimal_light", "founder_brief", "memory_archive"), ("split_story", "timeline_steps", "soft_cta")),
    BackgroundPreset("blue_crumple", "bg_09.jpeg", "paper", "light", "medium", ("magazine", "carddeck", "terminal"), ("founder_brief", "memory_archive", "research_mono"), ("checklist_stack", "timeline_steps", "split_story")),
    BackgroundPreset("grain_diagonal", "bg_10.jpeg", "grain", "medium", "medium", ("terminal", "poster", "magazine"), ("research_mono", "growth_black", "editorial_premium"), ("stat_panel", "comparison_grid", "quote_poster")),
    BackgroundPreset("lime_flower", "bg_11.jpeg", "bold", "light", "high", ("poster", "carddeck"), ("creator_bold", "minimal_light"), ("hero_center", "quote_poster", "soft_cta")),
)


BACKGROUND_PRESET_MAP = {preset.preset_id: preset for preset in BACKGROUND_PRESETS}


def pick_background_preset(
    layout_style: str,
    theme_hint: str,
    slide_role: str,
    archetype: str,
) -> BackgroundPreset | None:
    candidates: list[tuple[int, BackgroundPreset]] = []
    for preset in BACKGROUND_PRESETS:
        score = 0
        if layout_style in preset.fit_styles:
            score += 5
        if theme_hint in preset.fit_themes:
            score += 4
        if archetype in preset.fit_archetypes:
            score += 3
        if slide_role == "hook" and "hero_center" in preset.fit_archetypes:
            score += 2
        if slide_role == "cta" and "soft_cta" in preset.fit_archetypes:
            score += 2
        if score:
            candidates.append((score, preset))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1].preset_id))
    return candidates[0][1]


@lru_cache(maxsize=64)
def load_background_preset_bytes(preset_id: str) -> bytes:
    preset = BACKGROUND_PRESET_MAP[preset_id]
    return preset.path.read_bytes()


@lru_cache(maxsize=64)
def load_background_preset_data_url(preset_id: str) -> str:
    return image_bytes_to_data_url(load_background_preset_bytes(preset_id), "image/jpeg")


def load_background_preset_buffer(preset_id: str) -> BytesIO:
    return BytesIO(load_background_preset_bytes(preset_id))
