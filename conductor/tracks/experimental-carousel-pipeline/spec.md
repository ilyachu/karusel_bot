# Track: Experimental Carousel Pipeline as Separate Test Button

**Status:** Draft → awaiting approval
**Track ID:** `experimental-carousel-pipeline`
**Created:** 2026-06-16
**Owner:** conductor (planning phase)

---

## 1. Problem

The current production carousel pipeline renders slides via `services/html_renderer.py`. The renderer accepts a lot of freedom per slide (`html_body` from the LLM, custom backgrounds, preset backgrounds, multiple visual modes, four layout styles). This freedom is the source of visual instability:

- LLM-generated `html_body` can produce low-contrast text.
- Custom or preset photo backgrounds can make text unreadable.
- The "strong" overlay rule in `services/html_renderer.py` is a guardrail, not a structural solution.

The team needs to **measure** whether a stricter, deterministic template renderer — separate from the production path — improves visual stability, **without** breaking the production path during the experiment.

## 2. Goal

Add a **second**, opt-in rendering path that:

- Reuses the existing carousel plan and layout specs produced by the production pipeline.
- Renders the same content through a small, deterministic template system (4 slide types: `hook`, `body`, `list`, `cta`).
- Produces 1080x1350 PNGs with hard readability rules.
- Is triggered by a separate inline button on the final "✅ Карусель готова" message.
- Saves its own export package under a `-exp` suffix with `render_mode="experimental-datatalks"`.

**The production renderer must keep working unchanged.**

## 3. Non-Goals

- Replace the production renderer globally.
- Remove `services/html_renderer.py`.
- Add Node, Nunjucks, React, Next.js, or any new runtime dependency.
- Change cover generation (`services/cover_renderer.py`).
- Change admin publishing logic.
- Auto-deploy to production.

## 4. UX

### Button placement

After the existing "✅ Карусель готова" message, add a new button row **for the admin only**:

```text
[🧪 Тестовый рендер]   callback_data = carousel_exp_render:<export_id>
```

This is **separate** from the existing admin-only publish buttons (Instagram, Threads, Meta). Visibility: `callback.from_user.id == ADMIN_ID` (the same condition that gates the existing publish buttons in `run_insta_auto_pipeline`).

### User flow

1. Admin (or any user) generates a carousel through the normal pipeline.
2. The "✅ Карусель готова" message shows publish buttons (admin only) and the new "🧪 Тестовый рендер" button (admin only).
3. Admin clicks "🧪 Тестовый рендер".
4. Bot answers the callback (silent — no popup).
5. Bot sends a status message: "🧪 Готовлю экспериментальный рендер…"
6. Bot loads the export package, rebuilds `layout_specs` from the saved `carousel_plan`, renders experimental PNGs.
7. Bot saves a new export package with `render_mode="experimental-datatalks"`.
8. Bot sends the experimental PNGs as a media group.
9. Bot sends a short caption: "🧪 Экспериментальный рендер. Сравни с обычным."
10. Bot sends a final status: "✅ Экспериментальный рендер готов. Export: <new_export_id>".

### Failure

If the experimental render fails for any reason (Playwright unavailable, mapping error, IO error), the bot:

- Sends a short message: "⚠️ Экспериментальный рендер не удался: <reason>."
- Does **not** raise, does **not** affect the production package.

## 5. Architecture

### New module: `services/experimental_carousel_renderer.py`

A single, self-contained module. Public surface:

```python
@dataclass(frozen=True)
class ExperimentalSlide:
    type: str  # one of: "hook", "body", "list", "cta"
    title: str
    body: str
    items: tuple[str, ...] = ()
    badge: str = ""
    highlight: str = ""


def map_layout_spec_to_experimental_slide(spec: LayoutSpec) -> ExperimentalSlide:
    """Map a production LayoutSpec into the experimental slide schema.
    
    Mapping rules:
    - role == "hook"      -> type="hook"
    - role == "cta"       -> type="cta"
    - density == "high"   -> type="list" IF body splits into >=2 short bullets
                             ELSE type="body"
    - default             -> type="body"
    
    The LLM-generated spec.html_body is NEVER read.
    """


def build_experimental_slide_html(
    slide: ExperimentalSlide,
    logo_text: str = "chu ai",
    custom_background_data_url: str = "",
    preset_background_data_url: str = "",
) -> str:
    """Build a complete 1080x1350 HTML document for the slide.
    
    Returns a string of HTML. Caller is responsible for rendering.
    
    Readability rules (always applied):
    - base background: #0a0a0a (dark)
    - text color: #f8fafc
    - if custom_background_data_url OR preset_background_data_url is present:
      - full-bleed external image at z-index 0
      - linear-gradient overlay rgba(7,10,18,0.62) -> rgba(7,10,18,0.76) at z-index 1
      - text forced to color:#f8fafc, opacity:1, text-shadow
    - body/list content inside a semi-transparent panel
    - no external fonts (system stack) to keep first iteration portable
    """


def render_experimental_carousel(
    layout_specs: list,
    logo_text: str = "chu ai",
    custom_background_data_url: str = "",
    preset_background_data_url: str = "",
) -> list[bytes]:
    """Render a list of LayoutSpecs to a list of PNG bytes.
    
    Synchronous. Caller wraps in asyncio.to_thread(...).
    Uses Playwright Chromium. Falls back to a Pillow-based stub
    (single-color image with text) if Playwright fails — never raises.
    """
```

### Mapping helper: `list` bullet split

In `map_layout_spec_to_experimental_slide`, for `density="high"`:

- Split `spec.body` on `\n` first. If that yields ≥2 non-empty lines → use as `items`.
- Else, split on `. ` (period+space) and filter fragments by length ≤ 80 characters. If ≥2 remain → use as `items`.
- Else → fall back to `type="body"` with the full `body` text.

This rule is part of the spec so the tests can pin it.

### Renderer

- Reuses `playwright.sync_api.sync_playwright` (already in `requirements.txt`).
- Viewport: 1080x1350, device_scale_factor=1.
- `page.set_content(html, wait_until="load")`.
- `page.screenshot(type="png", clip={"x":0,"y":0,"width":1080,"height":1350})`.
- Pillow fallback: a stub PNG (dark background, title centered, body truncated) — same shape as `services/html_renderer.py`'s fallback. Reuses `image_bytes_to_data_url` is not needed here.
- The fallback is **non-fatal**: log a warning, return the stub bytes.

### Callback handler: `handlers/carousel_flow.py`

Add:

```python
@router.callback_query(F.data.startswith("carousel_exp_render:"))
async def carousel_experimental_render(callback: types.CallbackQuery):
    await callback.answer()
    export_id = callback.data.split(":", 1)[1]

    if not (callback.from_user and callback.from_user.id == ADMIN_ID):
        await callback.message.answer("⚠️ Тестовый рендер доступен только админу.")
        return

    export_record = get_export_package(export_id)
    if not export_record:
        await callback.message.answer("⚠️ Export package не найден. Сгенерируйте карусель заново.")
        return

    status = await callback.message.answer("🧪 Готовлю экспериментальный рендер…")
    try:
        package = await asyncio.to_thread(
            _build_experimental_export_package,
            export_record,
        )
    except Exception as exc:
        logging.exception("Experimental render failed")
        await status.edit_text(f"⚠️ Экспериментальный рендер не удался: {exc}")
        return

    media_group = [
        InputMediaPhoto(
            media=BufferedInputFile(
                png,
                filename=f"experimental_slide_{index+1:02d}.png",
            )
        )
        for index, png in enumerate(package.pngs)
    ]
    await callback.message.answer_media_group(media_group)
    await callback.message.answer(
        f"🧪 Экспериментальный рендер. Сравни с обычным.\n\n"
        f"Export: {package.export_id}"
    )
    await status.edit_text("✅ Экспериментальный рендер готов.")
```

A small private helper `_build_experimental_export_package(export_record)` (lives in the same file) does:

1. `package = load_export_package(export_record["export_dir"])`
2. `carousel_plan = CarouselPlan(**package.metadata["carousel_plan"])` (rebuild from dict)
3. `layout_specs = build_instagram_layout_specs(carousel_plan, visual_mode=carousel_plan.theme_hint, layout_style=carousel_plan.layout_style)`
4. Resolve `custom_background_data_url` (currently not stored as data URL — only as `bool` flag in metadata; see Open Question 1 below)
5. Resolve `preset_background_data_url` from `preset_background_ids` via `services/background_registry.py`
6. `pngs = await-equivalent: render_experimental_carousel(layout_specs, ...)` via `asyncio.to_thread` at the handler level
7. Save a new export package: `build_instagram_export(..., extra_metadata={"render_mode": "experimental-datatalks", "parent_export_id": export_id, "carousel_plan": asdict(carousel_plan), "layout_specs": [s.to_dict() for s in layout_specs]})`
8. `save_export_package(new_export_id, chat_id, new_dir, slug, theme, "experimental-datatalks")`
9. Return a small dataclass with `pngs` and `export_id`.

### Button row in `run_insta_auto_pipeline`

Currently:

```python
action_rows = []
if message.from_user and message.from_user.id == ADMIN_ID:
    action_rows.append([...publish...])
    action_rows.append([...meta...])
actions = InlineKeyboardMarkup(inline_keyboard=action_rows) if action_rows else None
```

Change to:

```python
action_rows = []
if message.from_user and message.from_user.id == ADMIN_ID:
    action_rows.append([...publish...])
    action_rows.append([...meta...])
    action_rows.append([
        InlineKeyboardButton(
            text="🧪 Тестовый рендер",
            callback_data=f"carousel_exp_render:{export_id}",
        )
    ])
actions = InlineKeyboardMarkup(inline_keyboard=action_rows) if action_rows else None
```

The button is added inside the same admin gate, so non-admin users continue to see no buttons.

## 6. Files to Touch

| File | Change |
|------|--------|
| `services/experimental_carousel_renderer.py` | NEW. Public surface as above. |
| `handlers/carousel_flow.py` | Add callback handler + button row. Add `_build_experimental_export_package` private helper. |
| `tests/test_experimental_carousel_renderer.py` | NEW. Behavior tests. |
| `tests/test_flow_structure.py` | Add AST/structural assertions. |

## 7. Acceptance Criteria

The track is complete when:

1. The production carousel generation pipeline is unchanged (`rtk pytest` passes for the existing `test_html_renderer.py` and `test_layout_engine.py`).
2. After a successful carousel generation, the admin sees a new "🧪 Тестовый рендер" button under the existing admin publish buttons.
3. Clicking that button:
   - does not re-run the LLM;
   - loads the saved `carousel_plan` and rebuilds `layout_specs`;
   - renders the same content through the experimental deterministic templates;
   - sends the experimental PNGs as a media group;
   - sends a short caption;
   - saves a new export package with `render_mode="experimental-datatalks"`.
4. Non-admin users do **not** see the button (AST test confirms the `ADMIN_ID` gate).
5. Experimental slides are 1080x1350 (test asserts on rendered HTML/viewport).
6. Text is readable over custom/preset backgrounds: experimental HTML contains the readability CSS rules (test asserts on HTML string).
7. `spec.html_body` from the LLM is never read by the experimental renderer (test asserts that no `html_body` substring leaks into the output).
8. Long body text is HTML-escaped (test asserts `<script>` is escaped, not executed).
9. Mapping `LayoutSpec → ExperimentalSlide` follows the rules in §5 (unit tests for `hook`, `body`, `list`, `cta` paths and the density-high fallback).
10. No secrets in code, no new runtime dependencies, no Node/React.
11. All tests pass: `rtk pytest tests/test_experimental_carousel_renderer.py tests/test_flow_structure.py` and `rtk pytest`.
12. The uncommitted readability changes in `services/html_renderer.py` and `tests/test_html_renderer.py` are **not** reverted.

## 8. Open Questions / Risks

- **Open Question 1**: `metadata.custom_background` is currently a `bool`, not a data URL. To re-render with the custom background, the experimental renderer needs the bytes. Two options:
  - (a) Persist the data URL into `metadata.custom_background_data_url` at the end of `run_insta_auto_pipeline` (small, additive change).
  - (b) Pass `custom_background_data_url=None` and skip the custom-background branch in the experimental renderer.
  - Default for first iteration: **(a)** — persist a data URL only when the custom branch was used. This is a one-line change in `run_insta_auto_pipeline` and keeps the experiment fair.
- **Risk**: Pillow fallback stub may visually underwhelm. Documented as expected; the experimental pipeline is meant to be tested with Chromium enabled.
- **Risk**: 10+ slide carousels may take 5–10s to render via Playwright. Acceptable for an admin-only test button. Documented in the "Failure" section so the user knows the wait is normal.
