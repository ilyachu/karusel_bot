# Insta Auto product UX and carousel pipeline plan

Date: 2026-04-25
Scope: `/Users/ilyachumachenkov/Documents/контент мопед/karusel_bot`

## Requirements Summary

Goal: make carousel generation feel like one coherent Instagram product flow, not several technical prototypes stitched together.

Primary requirements:
- Keep the fast default path: user sends text or voice and receives a publish-ready carousel.
- Make visual choices understandable in product language: calm, contrast, facts, memo, not internal theme names.
- Make typography choices understandable: readable, big poster, memo, data, not raw font names.
- Diversify carousel slides so every carousel is not visually identical.
- Fix the broken custom cover/background path.
- Add/clarify 16:9 cover generation, while keeping Instagram feed carousel defaults safe.
- Reduce text bugs in generated slides and Telegram preview.
- Preserve existing Instagram and Threads publishing behavior.

## Evidence From Code

- `handlers/common.py:16-178` already contains a clearer `Insta Auto` setup model with text style, visual preset, typography/grid, and size, but it is still a UI layer only. `insta_card_format` is shown to users, but generation uses `insta_visual_mode` in `handlers/carousel_flow.py:274-290`; the card format is mostly a label.
- `handlers/carousel_flow.py:242-405` is the best current pipeline: analyze text, generate Instagram plan, enforce CTA, choose theme, render via HTML, export, caption, Threads summary, and publish buttons.
- The old `Создать карусель` path uses a separate flow in `handlers/carousel_flow.py:602-1280`. It has manual slide count, rewrite style, JSON editing, visual selection, text position, and in many cases no caption/export/publish package.
- `handlers/carousel_flow.py:780` and `handlers/carousel_flow.py:1519` both define `ask_visual_method`. The second definition overwrites the first at module runtime. Calls from the normal flow at `handlers/carousel_flow.py:767`, `778`, and `1078` therefore resolve to the fast-mode visual helper and can put users into `fast_mode_choosing_visual`.
- Fast mode is nominally disabled at `handlers/carousel_flow.py:1355-1362`, but its callbacks and helpers remain active from `handlers/carousel_flow.py:1364-1773`. This creates hidden shared behavior and makes the standard flow harder to reason about.
- The uploaded cover in the old flow is used as a first-slide background at `handlers/carousel_flow.py:1228-1231`, then rendered through the older `render_slide` path. It is not passed through the better standalone cover generator or a style-aware cover pipeline.
- In `Insta Auto`, custom background bytes force `render_layout_spec` / Pillow fallback at `handlers/carousel_flow.py:297-305`, so uploaded images bypass the HTML renderer and lose the richer editorial/brief/data compositions.
- Standalone covers already support `wide`, `post`, and `story` in `services/cover_renderer.py:11-15`, and the UI exposes 16:9 at `handlers/cover_flow.py:190-196`.
- The standalone cover uploader embeds the uploaded image as a data URL at `handlers/cover_flow.py:140-144`; the renderer overlays it with fixed opacity/filter values at `services/cover_renderer.py:203-217`. There is no focal-point handling, contrast-aware text treatment, or Instagram-safe export variant.
- Theme names in `services/layout_engine.py:109-123` and `utils/background_styles.py:26-47` are mostly internal/English. This conflicts with the desired UX language.
- The final action row in `handlers/carousel_flow.py:379-385` exposes `Prepare Meta Publish`, which is developer-facing and should be hidden or moved to an advanced/admin path.
- Text preview uses Telegram Markdown with raw generated text at `handlers/carousel_flow.py:711` and `1071`; underscores, brackets, or malformed generated text can break previews.
- CTA is currently forced by `enforce_default_cta_slide` at `services/layout_engine.py:458-476`. The classic default says "Подписывайтесь на канал", which is less precise for Instagram profile publishing.

## Instagram Format Note

For Instagram API image publishing, Meta's current documented image range is 4:5 to 1.91:1, JPEG, max 8 MB, width 320-1440. That means 16:9 (1.78:1) is inside the allowed aspect-ratio range, but it is a landscape feed asset and will usually be weaker for text-heavy carousels than 4:5.

Product decision:
- Keep carousel default as 4:5 `1080x1350`.
- Add 16:9 as "широкая обложка" for cross-posting, YouTube/Telegram/site previews, and occasional Instagram landscape posts.
- If the 16:9 asset is intended for Instagram API publishing, export an API-safe JPEG such as `1440x810` or `1080x608`, not the current `1920x1080` PNG-only cover output.

## Decision Drivers

1. One mental model for users: "send material -> choose/auto style -> preview -> publish".
2. One technical pipeline for all Instagram-ready carousel outputs.
3. Clear product style packs instead of exposing internal renderer/theme names.
4. Preserve publishing flow and export metadata.
5. Small, reversible diffs with tests before cleanup.

## Viable Options

### Option A: Patch only labels and prompts

Pros:
- Smallest diff.
- Low risk to publishing.

Cons:
- Does not fix duplicate helper/function overwrite.
- Does not unify old and Insta Auto pipelines.
- Custom background/cover quality remains inconsistent.

Verdict: not enough.

### Option B: Make Insta Auto the canonical pipeline, route normal creation into it

Pros:
- Reuses the best current path: plan, layout specs, HTML render, export, caption, publish.
- Removes duplicated fast/legacy decision trees.
- Fits the user's desired product direction.

Cons:
- Requires careful handler cleanup and regression tests around state transitions.
- Some old advanced controls need to become "advanced" or be removed.

Verdict: recommended.

### Option C: Full renderer redesign now

Pros:
- Could produce the highest visual jump.

Cons:
- Too broad for the current risk surface.
- Publishing and flow bugs should be fixed before a large visual rewrite.

Verdict: defer until after pipeline consolidation.

## Recommended Product Model

Introduce a single product-level style concept:

- `auto_best`: bot chooses based on content.
- `calm`: calm colors, readable typography, clean editorial layout.
- `contrast`: cover-like high contrast, big poster typography, stronger visual rhythm.
- `memo`: strict business/product memo.
- `facts`: data/fact layout for numbers, tools, comparisons, news.

The user-facing screen should not expose separate internal theme and layout terms by default. It can say:

- "Стиль: Авто"
- "Цвет и дизайн: Спокойный"
- "Типографика: Читабельная"
- "Формат: 4:5 Instagram"

Advanced settings can still exist, but the default user path should be one style choice, not four blocks.

## Implementation Plan

### Phase 0: Lock current behavior with tests

Add focused tests before cleanup:
- Standard flow helper identity: normal preview should set `CarouselFlow.choosing_visual_method`, not fast-mode state.
- `Insta Auto` style selection maps user-facing style keys to theme + visual mode deterministically.
- Uploaded custom background in `Insta Auto` preserves the chosen visual mode and does not silently downgrade the layout model.
- Cover format tests for 4:5, 16:9, 9:16 remain passing.

Run:
- `python3 -m unittest tests.test_layout_engine tests.test_html_renderer tests.test_cover_renderer tests.test_gemini_client`
- Then full suite once handler tests are added.

### Phase 1: Untangle handlers

Files:
- `handlers/carousel_flow.py`
- `utils/states.py`
- tests for handler/state helpers

Steps:
- Rename the first visual helper to something explicit like `ask_standard_visual_method`.
- Rename the second to `ask_fast_visual_method` or remove fast-mode helpers if truly unused.
- Remove duplicate `choosing_text_position` in `utils/states.py`.
- Decide whether fast mode is dead code. If disabled, remove or quarantine its callbacks so it cannot affect normal flow.
- Ensure `Создать карусель` cannot route into fast-mode states.

Acceptance:
- No duplicate function names for flow helpers.
- Normal carousel and Insta Auto state transitions are deterministic.
- Existing publishing callbacks remain unchanged.

### Phase 2: Make Insta Auto canonical

Files:
- `handlers/common.py`
- `handlers/carousel_flow.py`
- optionally `services/carousel_pipeline.py`

Steps:
- Extract the core generation function from `run_insta_auto_pipeline` into a reusable service/helper that accepts:
  - source text
  - rewrite style
  - product style pack
  - optional custom background/cover
  - chat/user context
- Route `Создать карусель` either directly to this pipeline or to a light pre-preview step that uses the same pipeline after approval.
- Keep old manual JSON editing out of the default path; move it to an explicit advanced/edit action after preview.
- Replace final action labels:
  - `Опубликовать в Instagram`
  - `Опубликовать в Threads`
  - `Изменить стиль`
  - `Перегенерировать`
  - hide `Prepare Meta Publish` unless admin/advanced mode.

Acceptance:
- Both entry points produce export package + caption + publish buttons.
- User sees one coherent result summary: content type, style, slide count, caption.
- Publishing callback IDs and export storage remain compatible.

### Phase 3: Productize style packs

Files:
- `handlers/common.py`
- `services/layout_engine.py`
- `services/html_renderer.py`
- tests in `tests/test_layout_engine.py` and `tests/test_html_renderer.py`

Steps:
- Add a `STYLE_PACKS` map or equivalent:
  - `calm -> memory_archive/editorial/readable`
  - `contrast -> growth_black/editorial or data/poster`
  - `memo -> founder_brief/brief/readable`
  - `facts -> research_mono/data/mono`
  - `auto_best -> policy`
- Make typography part of the style pack rather than a separate confusing low-level mode.
- For `calm`, prefer readable sans/system body and restrained colors.
- For `contrast`, use stronger cover-like titles and darker/high-contrast tokens.
- Add variation by slide role: cover, context, stat, checklist, quote, CTA should visibly differ within one carousel.

Acceptance:
- Same source text rendered with `calm` and `contrast` produces visibly different theme + layout specs.
- `auto_best` still chooses based on content signals.
- Layout tests prove role/variant diversity.

### Phase 4: Fix uploaded background and cover quality

Files:
- `handlers/carousel_flow.py`
- `handlers/cover_flow.py`
- `services/cover_renderer.py`
- `services/html_renderer.py`
- `services/image_renderer.py`

Steps:
- Stop treating uploaded cover as just a raw first-slide background in the old renderer.
- For carousel cover upload, use it as a background/image layer inside the same `LayoutSpec`/HTML renderer or a cover-specific plan.
- For standalone cover upload, add style-aware contrast overlays:
  - dark overlay for bright images
  - light/tinted overlay for dark images
  - safe text zones
  - consistent crop/fill behavior
- Preserve 4:5 as Instagram carousel default.
- Add explicit 16:9 cover generation as a separate cover format, with wording "широкая обложка".
- For Instagram API-safe output, add a JPEG export path if 16:9 is used for publishing.

Acceptance:
- Uploaded image does not produce unreadable typography.
- Uploaded cover/background still respects the selected style.
- 16:9 cover is generated and documented as wide/cross-platform, not default carousel format.

### Phase 5: Reduce text bugs

Files:
- `services/gemini_client.py`
- `handlers/carousel_flow.py`
- tests in `tests/test_gemini_client.py`

Steps:
- Extend carousel plan prompt to return `content_type`: educational, opinion, checklist, story_case, promo_offer, quote_manifesto, news_tool.
- Add local normalization/validation:
  - title max length
  - body max length
  - no broken ellipses in supporting cards
  - no CTA except final slide
  - no raw Markdown-breaking preview text
- Escape Telegram preview or send preview without Markdown.
- Replace JSON manual editing with simpler edit actions later:
  - edit caption
  - regenerate text
  - change style
  - advanced JSON edit hidden behind a deliberate button.

Acceptance:
- Generated previews do not fail due to Markdown punctuation.
- Final slide CTA is product-appropriate for Instagram.
- Captions stay under Instagram's 2200 character limit and avoid invented links.

### Phase 6: Verification and deployment

Run locally:
- `python3 -m unittest`
- render smoke tests for `calm`, `contrast`, `memo`, `facts`
- manual Telegram dry run if tokens are available:
  - `🚀 Insta Auto`
  - `Создать карусель`
  - custom background
  - standalone cover 4:5 and 16:9
  - publish button visibility

Production deploy after local pass:
- SSH to production path.
- Build container.
- Run existing Instagram/Threads publisher tests inside container.
- Do one non-publishing generation smoke test with the bot.

## Risks and Mitigations

- Risk: touching handlers can break Telegram state flow.
  Mitigation: add state-transition tests and keep changes small.
- Risk: hiding `Prepare Meta Publish` removes an admin capability.
  Mitigation: keep callback, move button behind admin/advanced flag.
- Risk: visual changes regress readability.
  Mitigation: render sample slides for each style and inspect before deploy.
- Risk: Instagram API format assumptions around PNG/JPEG and 16:9.
  Mitigation: keep publish carousel default at 4:5; add API-safe JPEG handling only when publishing wide images.

## Not In Scope For First Implementation Pass

- New external dependencies.
- Full redesign of all renderer CSS.
- Real visual AI generation of backgrounds.
- Changing Instagram/Threads publishing API logic except labels/visibility and export format safeguards.

## Current Verification Done During Planning

- Ran targeted existing tests:
  - `python3 -m unittest tests.test_layout_engine tests.test_html_renderer tests.test_gemini_client tests.test_cover_renderer`
  - Result: 36 tests passed.

