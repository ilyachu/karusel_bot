# HANDOFF: Experimental Carousel Pipeline as Separate Test Button

## TL;DR

User wants a second carousel rendering pipeline for A/B testing, not a replacement of the current production path.

Proposed split:
- **Base/render automation:** `DataTalksClub/carousel-automation`
- **Design logic ideas:** `itchernetski/threads-carousel-claude-skill`

Goal for next agent:
- Add a separate Telegram test button/callback for an experimental carousel renderer.
- Keep current production carousel generation untouched.
- Reuse the existing text planning pipeline where possible.
- Render the same generated `carousel_plan` through a new deterministic template renderer.
- Send result back to Telegram with metadata `render_mode="experimental-datatalks"`.

Do not deploy automatically unless user explicitly asks.

## Current Repo

Local repo:

```text
/Users/<REDACTED>/karusel_bot
```

Production server:

```text
root@<REDACTED>
/root/karusel_bot_v2
container: karusel_bot_new
```

Use `rtk` prefix for shell commands in this repo.

## Important Current State

There are local uncommitted changes from the readability fix:

```text
services/html_renderer.py
tests/test_html_renderer.py
```

Do not revert them. They were already deployed to production for testing, but not committed at the time this handoff was written.

Those changes add:
- stronger overlay on external backgrounds;
- forced readable AI HTML text over backgrounds;
- regression tests for contrast guard.

## Why This Experiment

Current pipeline is functional but has had visual stability problems:
- LLM-generated `html_body` can create weak contrast;
- custom/preset backgrounds can make text unreadable;
- visual quality varies because the renderer has too many degrees of freedom.

The experimental pipeline should test whether a stricter schema + fixed templates improves output.

## Repositories Reviewed

### 1. DataTalksClub/carousel-automation

Repo:

```text
https://github.com/DataTalksClub/carousel-automation
```

Useful parts:
- JSON content input.
- Nunjucks HTML templates.
- CSS per frame type.
- Playwright headless rendering.
- PNG/PDF export.

Why it is a good base:
- It is already a backend-style render pipeline, not a UI-first app.
- It maps well to Telegram bot needs: data in, images out.
- It is deterministic and template-driven.

Main limitations:
- Default sizes are `630x1200`, `1080x1080`, and a single `1080x1350` Twitter resource mode.
- It does not include our current custom-background contrast logic.
- It has no Telegram integration.

### 2. itchernetski/threads-carousel-claude-skill

Repo:

```text
https://github.com/itchernetski/threads-carousel-claude-skill
```

Useful parts:
- `SlideData` schema.
- 12 slide types: `hook`, `body`, `cta`, `quote`, `stats`, `list`, `checklist`, `process`, `comparison`, `image`, `emoji`, `number`.
- Style axes: font x surface x accent x purpose.
- Adaptive typography logic.
- Good controlled design tokens.

Why not use as base:
- It is a Next.js/React UI template.
- Export is UI/browser-oriented through `html-to-image`.
- It adds a Node/React app stack if copied directly.
- It does not solve arbitrary uploaded background contrast out of the box.

Recommendation:
- Borrow schema and design rules.
- Do not copy the whole Next app into production.

## Current Production Carousel Flow

Main file:

```text
handlers/carousel_flow.py
```

Main function:

```python
async def run_insta_auto_pipeline(message: types.Message, text: str, state: FSMContext):
```

Current flow:

1. Validate input text.
2. Resolve target slide count via `resolve_target_slide_count`.
3. Generate plan:

```python
generate_instagram_carousel_plan(...)
parse_carousel_plan(...)
```

4. Enforce CTA and theme:

```python
enforce_default_cta_slide(...)
apply_theme_selection_policy(...)
apply_theme_override(...)
resolve_visual_mode(...)
```

5. Attach AI HTML:

```python
attach_slide_html_to_plan(...)
```

6. Convert to layout specs:

```python
build_instagram_layout_specs(...)
```

7. Render current images:

```python
render_layout_spec_html(...)
```

8. Package export:

```python
build_instagram_export(...)
save_export_package(...)
```

The experimental renderer should start after `carousel_plan` / `layout_specs` are ready. It should not duplicate the whole planning logic if avoidable.

## Desired UX

Add a separate test path. Options:

### Preferred Minimal UX

After normal carousel generation finishes, add an inline button:

```text
🧪 Тестовый рендер
```

Callback contains `export_id`:

```text
carousel_exp_render:{export_id}
```

When clicked:
- load export package metadata;
- reuse stored `carousel_plan` and/or `layout_specs`;
- render experimental images;
- send media group;
- send short caption: "Экспериментальный рендер. Сравни с обычным."

Why preferred:
- No new FSM path.
- No need to re-run LLM.
- Same content, fair visual comparison.
- Low risk to production generation.

### Alternative UX

Add a settings toggle before generation:

```text
Рендер: стандартный / experimental
```

This is more invasive and not recommended for first test.

## Implementation Plan

### Step 1. Add Experimental Renderer Module

Create:

```text
services/experimental_carousel_renderer.py
```

Recommended public function:

```python
def render_experimental_carousel(
    layout_specs: list,
    logo_text: str,
    custom_background_data_url: str = "",
    preset_background_data_urls: list[str] | None = None,
) -> list[bytes]:
    ...
```

Keep it pure/synchronous so handlers can call it through:

```python
await asyncio.to_thread(...)
```

First version can be Python-only HTML generation using existing Playwright dependency from `services/html_renderer.py`. Do not add Node/Nunjucks dependency initially unless necessary.

Reason:
- The core value is deterministic templates, not the exact DataTalks JS implementation.
- Avoid new runtime dependencies.
- Easier tests.

### Step 2. Use DataTalksClub Pattern, Not Full Copy

Implement a simple template system:

```text
services/experimental_templates/
  base.html
  styles.css
```

Or keep inline HTML/CSS inside `experimental_carousel_renderer.py` for first iteration if small.

Must support 1080x1350.

Do not introduce Nunjucks/Jinja unless needed.

### Step 3. Borrow Design Logic From threads-carousel

Implement a small internal schema:

```python
@dataclass(frozen=True)
class ExperimentalSlide:
    type: str
    title: str
    body: str
    badge: str = ""
    items: list[str] = field(default_factory=list)
    highlight: str = ""
```

Map current `LayoutSpec` to this schema.

Initial type mapping:

```text
role=hook       -> hook
role=cta        -> cta
density=high    -> list if body can split into short bullets
supporting_cards -> card/body variant
default         -> body
```

Keep first version simple:
- `hook`
- `body`
- `list`
- `cta`

Do not overbuild all 12 slide types initially.

### Step 4. Stable Readability Rules

Experimental renderer must guarantee readability:

- fixed dark surface by default;
- optional light surface only if no custom/preset background;
- if external background is present:
  - render image full-bleed;
  - add dark overlay `rgba(7,10,18,0.62-0.76)`;
  - use `#f8fafc` text;
  - force `opacity:1`;
  - text shadow;
  - body/list content inside semi-transparent panels.

Do not allow AI-generated HTML in this renderer.

### Step 5. Add Callback Handler

Add to:

```text
handlers/carousel_flow.py
```

New callback:

```python
@router.callback_query(F.data.startswith("carousel_exp_render:"))
async def carousel_experimental_render(callback: types.CallbackQuery, state: FSMContext):
    ...
```

Logic:

1. Parse `export_id`.
2. Use `get_export_package(export_id)`.
3. Load package with `load_export_package(export_dir)`.
4. Read metadata:

```python
metadata["carousel_plan"]
metadata["layout_specs"]
metadata["custom_background"]
metadata["preset_background_ids"]
```

5. Reconstruct `CarouselPlan` with `parse_carousel_plan` if needed.
6. Reconstruct layout specs with:

```python
build_instagram_layout_specs(...)
```

If `layout_specs` in metadata are easier to use, add a small reconstruction helper, but prefer rebuilding from `carousel_plan`.

7. Render experimental bytes.
8. Send media group.
9. Save as a separate export package if easy; otherwise just send for first iteration.

### Step 6. Add Button To Existing Result

At the bottom of `run_insta_auto_pipeline`, after export is saved and `export_id` exists, add button to `action_rows` for all users:

```python
action_rows.append(
    [InlineKeyboardButton(text="🧪 Тестовый рендер", callback_data=f"carousel_exp_render:{export_id}")]
)
```

Current admin publish buttons are only for admin. The test render button can be visible to the user who generated the carousel.

Important:
- If there are no admin buttons, `actions` currently becomes `None`.
- Make sure adding this row causes `actions` to exist for normal users too.

### Step 7. Tests

Add tests without requiring Playwright if possible.

Recommended tests:

```text
tests/test_experimental_carousel_renderer.py
```

Test cases:
- renderer builds HTML containing 1080/1350 dimensions;
- custom background adds dark overlay and readable text color;
- no AI `html_body` is used;
- long text is escaped and does not inject HTML;
- mapping from `LayoutSpec` to experimental slide type works.

Add flow structure test in:

```text
tests/test_flow_structure.py
```

Check:
- `carousel_exp_render:` callback exists;
- action button text `Тестовый рендер` exists;
- metadata render mode uses `experimental-datatalks` if saved.

Run:

```bash
rtk pytest tests/test_experimental_carousel_renderer.py tests/test_flow_structure.py
rtk pytest
```

## Acceptance Criteria

The task is complete when:

- Current normal carousel generation still works unchanged.
- Generated normal carousel has a new button `🧪 Тестовый рендер`.
- Clicking button renders the same content through the experimental deterministic templates.
- Bot sends experimental images as a media group.
- Experimental slides are 1080x1350.
- Text is readable over custom/preset backgrounds.
- Tests pass.
- No secrets committed or logged.

## Non-Goals

Do not:
- replace current renderer globally;
- remove `services/html_renderer.py`;
- add React/Next.js to production;
- add Node/Nunjucks unless Python-only version is clearly insufficient;
- change cover generation;
- change admin publishing logic;
- deploy without explicit user approval.

## Suggested Minimal HTML Direction

Use 4 deterministic layouts:

### hook

Large title, centered/left, optional badge.

### body

Title + paragraph inside readable panel.

### list

Title + 3-5 bullet items. Split body by newline or sentence only if safe.

### cta

Large final statement + logo/handle.

Shared CSS:

```css
body {
  width: 1080px;
  height: 1350px;
  margin: 0;
  overflow: hidden;
  background: #0a0a0a;
  color: #f8fafc;
}

.slide {
  width: 1080px;
  height: 1350px;
  position: relative;
  padding: 80px;
}

.external-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  z-index: 0;
}

.overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(7,10,18,0.62), rgba(7,10,18,0.76));
  z-index: 1;
}

.content {
  position: relative;
  z-index: 2;
}

.panel {
  background: rgba(10,14,24,0.76);
  border: 1px solid rgba(255,255,255,0.20);
  border-radius: 32px;
  padding: 40px;
}
```

## Files Most Likely To Touch

```text
handlers/carousel_flow.py
services/experimental_carousel_renderer.py
tests/test_experimental_carousel_renderer.py
tests/test_flow_structure.py
```

Maybe:

```text
services/layout_engine.py
```

Avoid touching unless mapping helpers truly belong there.

## Deployment Notes

Only after user asks:

```bash
rtk sh -c 'cat handlers/carousel_flow.py | ssh root@<REDACTED> "cat > /root/karusel_bot_v2/handlers/carousel_flow.py"'
rtk sh -c 'cat services/experimental_carousel_renderer.py | ssh root@<REDACTED> "cat > /root/karusel_bot_v2/services/experimental_carousel_renderer.py"'
rtk ssh root@<REDACTED> 'cd /root/karusel_bot_v2 && docker compose down bot && docker compose up -d --build bot'
rtk ssh root@<REDACTED> 'cd /root/karusel_bot_v2 && docker compose logs --tail=100 bot'
```

No rsync. No secrets.

## Final Report Expected From Agent

Report:
- changed files;
- how test button works;
- what was verified;
- screenshots/output paths if local render was produced;
- residual risks.

