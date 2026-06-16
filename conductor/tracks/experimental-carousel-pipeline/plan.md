# Plan — Experimental Carousel Pipeline

**Status:** Draft → awaiting approval
**Track:** [./](./)

Each task is small enough to verify in one cycle. Tests after every behavioral change.

---

## Task 1. Create the experimental renderer module skeleton

**File:** `services/experimental_carousel_renderer.py` (NEW)

**What:**
- Module docstring explaining the goal: opt-in experimental renderer, deterministic templates, ignores `html_body`.
- Define `@dataclass(frozen=True) class ExperimentalSlide` with fields `type`, `title`, `body`, `items: tuple[str, ...] = ()`, `badge: str = ""`, `highlight: str = ""`.
- Define `map_layout_spec_to_experimental_slide(spec: LayoutSpec) -> ExperimentalSlide` with the mapping rules from spec §5.
- Define `build_experimental_slide_html(slide, logo_text, custom_background_data_url, preset_background_data_url) -> str` returning a complete HTML doc with the readability CSS from spec §5.
- Define `render_experimental_carousel(layout_specs, logo_text, custom_background_data_url, preset_background_data_url) -> list[bytes]` that:
  - builds HTML for each spec;
  - tries `playwright.sync_api.sync_playwright` → 1080x1350 PNG;
  - on failure, logs a warning and returns a Pillow fallback PNG (dark BG, centered title, truncated body).
- All three functions synchronous; no `asyncio`.

**Verify:**
- `rtk python -c "from services.experimental_carousel_renderer import render_experimental_carousel, build_experimental_slide_html, map_layout_spec_to_experimental_slide, ExperimentalSlide; print('ok')"`
- `rtk python -c "from services.experimental_carousel_renderer import build_experimental_slide_html; from services.experimental_carousel_renderer import ExperimentalSlide; html = build_experimental_slide_html(ExperimentalSlide(type='hook', title='T', body='B')); assert '1080px' in html and '1350px' in html; print('ok')"`

**Done when:** module imports cleanly and a minimal call returns a string containing both `1080` and `1350` dimensions.

---

## Task 2. Persist custom-background data URL into metadata (Open Question 1)

**File:** `handlers/carousel_flow.py`

**What:** in `run_insta_auto_pipeline`, after the existing `update_export_metadata(...)` calls (around line 497), if `custom_bg_bytes` is set, add a second `update_export_metadata(export_dir, {"custom_background_data_url": image_bytes_to_data_url(custom_bg_bytes, custom_bg_mime or "image/jpeg")})`. This is additive — does not change the existing flow.

**Verify:** `rtk grep -n "custom_background_data_url" handlers/carousel_flow.py`

**Done when:** the metadata file written by the export package contains `custom_background_data_url` when a custom background was used.

---

## Task 3. Add the "🧪 Тестовый рендер" button to the admin result

**File:** `handlers/carousel_flow.py`

**What:** inside the `if message.from_user and message.from_user.id == ADMIN_ID:` block in `run_insta_auto_pipeline` (after the two existing `action_rows.append(...)` calls around lines 503-511), append:

```python
action_rows.append(
    [InlineKeyboardButton(
        text="🧪 Тестовый рендер",
        callback_data=f"carousel_exp_render:{export_id}",
    )]
```

**Verify:** `rtk grep -n "carousel_exp_render" handlers/carousel_flow.py`

**Done when:** the button text and `carousel_exp_render:` callback prefix both appear in the file, inside the admin-gated block.

---

## Task 4. Add the callback handler and the export-package builder

**File:** `handlers/carousel_flow.py`

**What:** append at the end of the file:

- Private helper `_build_experimental_export_package(export_record) -> ExperimentalExportPackage` that:
  - calls `load_export_package(export_record["export_dir"])`;
  - reconstructs `CarouselPlan` from `metadata["carousel_plan"]` via `CarouselPlan(**...)` after coercing `slides` back into a list of `SlidePlanEntry(**...)` objects;
  - calls `build_instagram_layout_specs(carousel_plan, visual_mode=carousel_plan.theme_hint, layout_style=carousel_plan.layout_style)` to rebuild `layout_specs`;
  - resolves `custom_background_data_url` from `metadata["custom_background_data_url"]` (default `""`) and `preset_background_data_url` by joining preset IDs into a single data URL or leaving empty for the first iteration (we will pass `""` and document that the preset branch renders the dark surface for v1);
  - calls `render_experimental_carousel(layout_specs, logo_text, custom_background_data_url, preset_background_data_url)` to get `pngs`;
  - calls `build_instagram_export(..., extra_metadata={"render_mode": "experimental-datatalks", "parent_export_id": export_id, "carousel_plan": asdict(carousel_plan), "layout_specs": [s.to_dict() for s in layout_specs]})`;
  - calls `save_export_package(new_export_id, chat_id, new_dir, slug, theme_hint, "experimental-datatalks")`;
  - returns a small `ExperimentalExportPackage` dataclass with `pngs`, `export_id`, `export_dir`.
- Public handler:

```python
@router.callback_query(F.data.startswith("carousel_exp_render:"))
async def carousel_experimental_render(callback: types.CallbackQuery):
    ...see spec.md §5 for the full body...
```

The handler calls the private helper via `await asyncio.to_thread(_build_experimental_export_package, export_record)` and then sends the media group.

**Verify:** `rtk python -c "from handlers.carousel_flow import carousel_experimental_render; print('ok')"`

**Done when:** the module imports cleanly and the callback prefix `carousel_exp_render:` exists in source.

---

## Task 5. Write behavior tests for the renderer

**File:** `tests/test_experimental_carousel_renderer.py` (NEW)

**What:** `unittest.TestCase` with the following test methods:

1. `test_build_html_uses_1080x1350_dimensions` — call `build_experimental_slide_html(ExperimentalSlide(type="body", title="T", body="B"))`, assert `1080px`, `1350px`, `width: 1080px`, `height: 1350px` in the result.
2. `test_build_html_uses_dark_surface_and_light_text` — assert `#0a0a0a` and `#f8fafc` in the HTML.
3. `test_custom_background_adds_dark_overlay_and_readable_text` — call with a non-empty `custom_background_data_url="data:image/png;base64,ZmFrZQ=="`, assert `linear-gradient`, `rgba(7,10,18,0.62)`, `rgba(7,10,18,0.76)`, `color: #f8fafc`, `opacity: 1`, `text-shadow` in the result.
4. `test_no_ai_html_body_leaks_into_experimental_html` — pass a `LayoutSpec` with `html_body="<script>alert(1)</script>LEAK"` via `build_experimental_slide_html` (after a quick path that exposes a hook for direct injection, or build an `ExperimentalSlide` and assert the field is not in the output), assert `LEAK` and `<script>` are absent.
5. `test_html_escapes_long_user_text` — pass a title with `<script>alert(1)</script>`, assert the substring appears as `&lt;script&gt;...` and the raw `<script>` is not present.
6. `test_map_hook_role` — `LayoutSpec(role="hook", title="X", body="Y")` → `ExperimentalSlide(type="hook", title="X", body="Y", items=())`.
7. `test_map_cta_role` — `LayoutSpec(role="cta", ...)` → `ExperimentalSlide(type="cta", ...)`.
8. `test_map_default_role_to_body` — `LayoutSpec(role="body", density="low", ...)` → `ExperimentalSlide(type="body", ...)`.
9. `test_map_density_high_with_newlines_to_list` — `LayoutSpec(role="body", density="high", body="A\nB\nC", ...)` → `ExperimentalSlide(type="list", items=("A","B","C"))`.
10. `test_map_density_high_without_newlines_short_sentences_to_list` — `LayoutSpec(role="body", density="high", body="Short one. Short two. Short three.", ...)` → `ExperimentalSlide(type="list", items=("Short one.","Short two.","Short three."))`.
11. `test_map_density_high_long_paragraph_falls_back_to_body` — `LayoutSpec(role="body", density="high", body=("This is a single very long sentence " * 8), ...)` → `ExperimentalSlide(type="body", items=())` (no list because splitting yields <2 fragments ≤80 chars).
12. `test_render_experimental_carousel_returns_one_png_per_spec` — pass two minimal `LayoutSpec`s, mock Playwright to return a 1x1 PNG, assert `len(result) == 2`, both are bytes.
13. `test_render_experimental_carousel_falls_back_when_playwright_unavailable` — patch `playwright.sync_api.sync_playwright` to raise, assert the function still returns a list of bytes (Pillow fallback).
14. `test_render_experimental_carousel_never_raises` — pass `[]`, assert result is `[]`.

**Verify:** `rtk pytest tests/test_experimental_carousel_renderer.py -v`

**Done when:** all 14 tests pass.

---

## Task 6. Write flow-structure tests

**File:** `tests/test_flow_structure.py` (append methods to existing `FlowStructureTests`)

**What:** add:

- `test_experimental_render_button_is_in_admin_block` — read `handlers/carousel_flow.py` source, assert `"🧪 Тестовый рендер"` and `"carousel_exp_render:"` are present, and the test fails if the button text is outside the `if message.from_user and message.from_user.id == ADMIN_ID:` block. Implementation: locate the admin block, search for the button text inside it.
- `test_experimental_render_callback_handler_exists` — assert `async def carousel_experimental_render` is defined.
- `test_experimental_renderer_module_exists` — assert `services/experimental_carousel_renderer.py` exists on disk and exports `render_experimental_carousel`, `build_experimental_slide_html`, `map_layout_spec_to_experimental_slide`, `ExperimentalSlide`.
- `test_production_html_renderer_changes_are_preserved` — assert the readability-fix substrings from the uncommitted diff are still present: `rgba(7, 10, 18, 0.56)`, `_external_background_text_guard_css`, `forced readable AI HTML text` (last one as a comment marker). This guards against accidental revert.

**Verify:** `rtk pytest tests/test_flow_structure.py -v`

**Done when:** the new tests pass alongside existing ones.

---

## Task 7. Full test suite + manual smoke

**What:**
- `rtk pytest` — entire suite must pass. No regression.
- (Optional, manual) Run a smoke render:

```bash
rtk python -c "
from services.layout_engine import parse_carousel_plan, build_instagram_layout_specs
from services.experimental_carousel_renderer import render_experimental_carousel
plan = parse_carousel_plan({
    'carousel': {'layout_style': 'magazine', 'theme_hint': 'founder_brief'},
    'slides': [
        {'index':1,'role':'hook','title':'Заголовок','body':'Тело','density':'low'},
        {'index':2,'role':'body','title':'Слайд 2','body':'Параграф','density':'low'},
    ],
})
specs = build_instagram_layout_specs(plan, layout_style='magazine')
pngs = render_experimental_carousel(specs)
print(len(pngs), [len(p) for p in pngs])
"
```

- Open one of the resulting PNGs and visually confirm readability.

**Verify:** `rtk pytest` returns 0 failures and the smoke command prints two byte counts > 0.

**Done when:** full suite is green, smoke output is sane.

---

## Task 8. Final report

**What:** reply to the user with:
- changed files (full list);
- new button behavior (with the exact callback prefix and visibility rule);
- what was verified (test counts, smoke output);
- any output paths if local render was produced;
- residual risks (Playwright availability in container, Pillow fallback visual quality, preset-background branch left empty for v1).

**Done when:** the user has all the info to decide on a deploy.

---

## Out of Scope (explicit)

- Deploying to `root@5.253.188.164` — only after explicit user "go ahead".
- Persisting `preset_background_data_url` into metadata — left for v2. v1 passes `""` and the experimental preset branch renders the dark surface; the comparison is still informative.
- Adding Jinja2 or any templating engine — first iteration is inline HTML strings.
- Touching `services/cover_renderer.py` or `handlers/cover_flow.py`.
- Removing or refactoring the readability fix in `services/html_renderer.py`.
