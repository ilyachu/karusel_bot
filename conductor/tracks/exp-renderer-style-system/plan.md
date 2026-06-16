# Plan — Experimental Renderer Style System + 3-Style Inline Preview

**Status:** Draft → awaiting approval
**Track:** [./](./)

Each task is small enough to verify in one cycle. Tests after every behavioral change.

---

## Task 1. Define the 4-axis style schema

**File:** `services/experimental_carousel_renderer.py`

**What:**
- Add `@dataclass(frozen=True) class StylePreset` with the fields from spec §5.
- Add 4 dicts: `FONT_STYLES`, `SURFACES`, `ACCENTS`, `BACKGROUNDS`.
- Add `STYLE_PRESETS` dict with exactly 3 entries: `dark_teal`, `paper_orange`, `white_coral`.
- Add module-level `DEFAULT_STYLE = STYLE_PRESETS["dark_teal"]`.
- All three preset ids must be present and resolve to distinct `(font_family, surface_bg, accent_color)` tuples (this is what makes them visually different).

**Verify:**
- `rtk python -c "from services.experimental_carousel_renderer import STYLE_PRESETS, StylePreset; assert set(STYLE_PRESETS) == {'dark_teal','paper_orange','white_coral'}; print('3 presets ok')"`
- `rtk python -c "from services.experimental_carousel_renderer import STYLE_PRESETS; presets = list(STYLE_PRESETS.values()); assert presets[0].surface_bg != presets[1].surface_bg != presets[2].surface_bg; assert presets[0].accent_color != presets[1].accent_color != presets[2].accent_color; print('presets distinct ok')"`

**Done when:** the dicts exist and the three ids are distinct in surface + accent.

---

## Task 2. Extend `ExperimentalSlide` and the mapper

**File:** `services/experimental_carousel_renderer.py`

**What:**
- Add `highlights: tuple[str, ...] = ()` field to `ExperimentalSlide`.
- Update `map_layout_spec_to_experimental_slide(spec, style: StylePreset | None = None)`:
  - Accept an optional `style` argument (defaults to `DEFAULT_STYLE`).
  - Copy `spec.highlight_words` (if any) into `ExperimentalSlide.highlights`.
  - If `style is None`, fall back to `DEFAULT_STYLE` for back-compat with existing tests.
- Existing tests that call `map_layout_spec_to_experimental_slide(spec)` (no `style`) must keep passing.

**Verify:**
- `rtk pytest tests/test_experimental_carousel_renderer.py -v` — all 18 existing tests still pass.

**Done when:** the 18 existing tests are still green and the new field is in place.

---

## Task 3. Extend `build_experimental_slide_html` with style support

**File:** `services/experimental_carousel_renderer.py`

**What:**
- Add `style: StylePreset | None = None` parameter. Default `None` → `DEFAULT_STYLE` (back-compat).
- Replace hardcoded `DARK_SURFACE` / `LIGHT_TEXT` / `PANEL_BG` with values from `style`.
- For light surfaces (`paper`, `white`), switch the external-bg overlay to a darker gradient that still guarantees readability. The rule: if `style.surface_bg` is **not** `#0a0a0a`/`#0a0e1a` and a custom background is present, use the dark overlay `rgba(7,10,18,0.62) → 0.76`. Otherwise, use a soft light overlay `rgba(255,255,255,0.18) → 0.30` to keep things readable.
- Emit a Google Fonts `<link>` in `<head>` with only the families the chosen style needs. URL is `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800|Playfair+Display:wght@400;600;700;800|Unbounded:wght@400;600;700;800&display=swap` filtered down to the actual family. Fallback stack: `<google-font>, system-ui, sans-serif`.
- Apply `style.background_css` as a CSS variable on `body` (or empty if `"none"`).
- Apply `style.accent_color` to a new CSS class `.hl { color: <accent>; font-weight: 700; }`.
- For hook titles, use `style.hook_font_family or style.font_family`.
- Implement `highlight_words` rendering: helper function `_wrap_highlights(text: str, highlights: tuple[str, ...]) -> str` that does whole-word matching (case-insensitive) and wraps each occurrence in `<span class="hl">{escaped match}</span>`. Apply to `title`, `body`, and each `item`.

**Verify:**
- `rtk pytest tests/test_experimental_carousel_renderer.py -v` — existing 18 tests must still pass.
- `rtk python -c "
from services.experimental_carousel_renderer import STYLE_PRESETS, build_experimental_slide_html, ExperimentalSlide
for preset in STYLE_PRESETS.values():
    html = build_experimental_slide_html(
        ExperimentalSlide(type='hook', title='Test', body='Body'),
        style=preset,
    )
    assert preset.surface_bg in html or preset.surface_bg.replace('#','') in html, f'{preset.id}: surface missing'
    print(preset.id, 'ok')
"`

**Done when:** all 3 styles render HTML containing their distinct surface color.

---

## Task 4. Extend `render_experimental_carousel` to accept style

**File:** `services/experimental_carousel_renderer.py`

**What:**
- Add `style: StylePreset | None = None` parameter.
- Default `None` → `DEFAULT_STYLE`.
- Pass `style` through to `build_experimental_slide_html`.
- Pillow fallback should also respect the style's surface/text colors (small change).

**Verify:**
- `rtk pytest tests/test_experimental_carousel_renderer.py -v` — all 18 still pass.

**Done when:** the signature is updated, existing tests pass, and the function works for the 3 preset ids.

---

## Task 5. Add tests for the new style system

**File:** `tests/test_experimental_carousel_renderer.py`

**What:** add a new test class `StyleSystemTests` with these tests:

1. `test_three_presets_exist` — `set(STYLE_PRESETS.keys()) == {"dark_teal", "paper_orange", "white_coral"}`.
2. `test_presets_have_distinct_surfaces` — surface_bg differs across all 3.
3. `test_presets_have_distinct_accents` — accent_color differs across all 3.
4. `test_presets_have_distinct_fonts` — font_family differs across all 3 (at least 2 unique values; `editorial` vs `clean` vs `minimal` are all different families).
5. `test_build_html_uses_style_surface` — for each preset, the surface color (or its RGB hex without `#`) appears in the rendered HTML.
6. `test_build_html_uses_style_accent` — for each preset, the accent color appears in the rendered HTML (in `.hl` class or as a CSS variable).
7. `test_build_html_uses_style_font` — for each preset, the font family name (e.g. "Inter", "Playfair Display", "Unbounded") appears in the rendered HTML.
8. `test_build_html_emits_google_fonts_link` — assert `<link` and `fonts.googleapis.com` are present in the HTML for non-system fonts.
9. `test_map_layout_spec_copies_highlight_words` — build a `LayoutSpec` with `highlight_words=["foo"]`, expect `ExperimentalSlide.highlights == ("foo",)`.
10. `test_highlight_words_become_hl_span` — render with `highlight_words=["Skills"]`, assert `<span class="hl">Skills</span>` is in the output.
11. `test_highlight_words_are_escaped` — pass `highlight_words=["<script>"]`, assert `<span class="hl">&lt;script&gt;</span>` is in the output, and no raw `<script>` survives.
12. `test_light_surface_with_external_bg_uses_dark_overlay` — call with `style=STYLE_PRESETS["paper_orange"]` and a custom background data URL; assert `rgba(7, 10, 18, 0.62)` is in the HTML.
13. `test_dark_surface_with_external_bg_keeps_soft_overlay` — call with `style=STYLE_PRESETS["dark_teal"]` and a custom background data URL; assert the dark overlay is also present (regression: existing behavior preserved).
14. `test_render_with_style_returns_pngs` — call `render_experimental_carousel([_make_spec(...)], style=STYLE_PRESETS["white_coral"])` with Playwright mocked; assert one PNG returned.
15. `test_default_style_is_dark_teal` — call `build_experimental_slide_html(ExperimentalSlide(...))` (no style); assert dark-teal surface color is in the HTML (back-compat assertion).

**Verify:** `rtk pytest tests/test_experimental_carousel_renderer.py -v` — all old 18 + new 15 = 33 tests pass.

**Done when:** the suite is green and StyleSystemTests covers all axes.

---

## Task 6. Update the callback handler and the button row

**File:** `handlers/carousel_flow.py`

**What:**
- In `run_insta_auto_pipeline`, **replace** the single "🧪 Тестовый рендер" admin button row with three rows:

```python
action_rows.append(
    [
        InlineKeyboardButton(text="🧪 Dark+Teal",   callback_data=f"carousel_exp_render:{export_id}:dark_teal"),
        InlineKeyboardButton(text="🧪 Paper+Orange", callback_data=f"carousel_exp_render:{export_id}:paper_orange"),
    ]
)
action_rows.append(
    [InlineKeyboardButton(text="🧪 White+Coral", callback_data=f"carousel_exp_render:{export_id}:white_coral")]
)
```

(Two rows: 2 + 1. Telegram will wrap onto 3 columns on wide clients.)

- In `carousel_experimental_render`, parse 3 segments: `parts = callback.data.split(":", 2)` → `export_id, style_id`. If `style_id` is missing, default to `dark_teal` (back-compat with any cached 2-segment buttons).
- Resolve `style_id` against `STYLE_PRESETS`. If unknown: send user-facing message "⚠️ Неизвестный стиль: <id>" and return.
- Pass the resolved `style` into `_build_experimental_export_package`.
- The status message and the caption include the preset label (e.g. "🧪 Dark+Teal — рендерю…").
- The new export package is created with `render_mode=f"experimental-datatalks-{style_id}"` in `extra_metadata` and a slug suffix `<slug>-<style_id>`.
- Save_exportPackage: `render_mode=f"experimental-datatalks-{style_id}"`.

**Verify:**
- `rtk grep -n "carousel_exp_render" handlers/carousel_flow.py` — three callback lines (one per style).
- `rtk grep -n "Dark+Teal\|Paper+Orange\|White+Coral" handlers/carousel_flow.py` — three button labels in source.
- `rtk python -c "from handlers.carousel_flow import carousel_experimental_render; print('ok')"`

**Done when:** the import works, the three buttons exist, and the handler accepts a 3-segment form.

---

## Task 7. Update `_build_experimental_export_package` to accept style

**File:** `handlers/carousel_flow.py`

**What:**
- New signature: `_build_experimental_export_package(export_record, style: StylePreset) -> _ExperimentalExportPackage`.
- Pass `style` into `render_experimental_carousel(..., style=style)`.
- Use `style.id` in `extra_metadata["render_mode"]` and in the export package `render_mode` field.
- Append `-<style.id>` to the source-text slug (clamped to 48 chars to keep `_slugify` happy).

**Verify:**
- `rtk pytest tests/test_flow_structure.py -v`

**Done when:** the helper signature is updated and the flow-structure tests pass.

---

## Task 8. Update flow-structure tests

**File:** `tests/test_flow_structure.py`

**What:** add:

- `test_three_experimental_style_buttons_exist` — read `handlers/carousel_flow.py`, assert that all three button labels exist in source: "🧪 Dark+Teal", "🧪 Paper+Orange", "🧪 White+Coral".
- `test_experimental_callback_supports_three_segments` — assert that the callback data string for the three styles (`carousel_exp_render:{export_id}:dark_teal` etc.) appears in source.
- `test_experimental_renderer_exports_style_presets_dict` — import the module and assert `STYLE_PRESETS` is exported and has exactly 3 keys.
- `test_production_html_renderer_changes_are_still_preserved` — the same readability-guard test from track 1, re-checked (paranoia guard).

**Verify:** `rtk pytest tests/test_flow_structure.py -v`

**Done when:** the 4 new tests pass and existing tests are still green.

---

## Task 9. Full test suite + manual smoke

**What:**
- `rtk pytest tests/` — full suite must pass.
- Manual smoke: render the same 4-slide carousel in all 3 styles. Save PNGs to `/tmp/exp_style_smoke/<style_id>/slide_*.png`. Visually inspect.

**Verify:** `rtk pytest` returns 0 failures; smoke output is sane (3 different-looking slide sets).

**Done when:** full suite is green, smoke output is 3 visually distinct sets.

---

## Task 10. Final report

**What:** reply to the user with:
- changed files;
- the 3 button labels and what each one produces;
- what was verified (test counts, smoke output, samples);
- residual risks (Google Fonts network dependency, light surface readability trade-off, 3-button Telegram layout).

**Done when:** the user has all the info to decide on a deploy.

---

## Out of Scope (explicit)

- Deploying to `root@<SERVER_IP>` — only after explicit user "go ahead".
- Exposing more than 3 style presets.
- Adding new slide types (quote / number / stats / checklist).
- Touching `services/cover_renderer.py` or `handlers/cover_flow.py`.
- Removing or refactoring the readability fix.
- Cleanup of accumulated experimental export packages on disk.
