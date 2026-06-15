# Render Quality Next Steps

Date: 2026-06-15

## Current Problem

Custom-background carousel output is visually unstable:

- User background can technically pass through the pipeline, but AI-generated root slide HTML can still dominate the composition.
- Text can be clipped at the canvas edges because AI root sections often use `width:1080px;height:1350px` without safe padding.
- Text contrast is unreliable because AI uses low opacity, muted colors, or background panels that become too transparent after post-processing.
- Auto background presets are now visible, but they need stricter contrast handling so text does not become dim.

Evidence from production exports:

- `/root/karusel_bot_v2/data/exports/20260615-150852-252202-переписки-в-telegram-и-whatsapp-выпадают-из-crm-/metadata.json`
- `render_mode=html-custom-bg`, `custom_background=True`, `preset_background_ids=[]`, `slides=4`
- Every AI `html_body` root section had `root_no_padding=True`.
- Every AI `html_body` had low-opacity styling patterns.

Related non-custom export:

- `/root/karusel_bot_v2/data/exports/20260615-151106-252202-переписки-в-telegram-и-whatsapp-выпадают-из-crm-/metadata.json`
- `render_mode=html`, `custom_background=False`, auto presets used.

## Root Cause

The pipeline uses AI-generated body-level HTML as the primary visual layer. This gives variety, but the AI output is not constrained enough:

- AI controls full canvas layout.
- AI controls root background.
- AI controls text opacity and color.
- AI can place content at `top:0`, `left:0`, or rely on exact 1080x1350 sizing with no safe area.

The renderer currently wraps AI HTML, but the wrapper does not yet enforce a strong enough production contract for readable Instagram slides.

## What To Do Next

1. Add an AI HTML safety normalizer before rendering.

Required behavior:

- Force safe padding or safe inset around the AI root.
- Prevent text from touching top/left/right/bottom edges.
- Convert full-canvas root backgrounds into readable translucent panels only when an external background exists.
- Strip or raise too-low `opacity` values on text/content elements.
- Add default text shadow or panel contrast for external backgrounds.

2. Add visual regression fixtures for the exact failure class.

Required fixtures:

- Custom background + AI root with no padding.
- Custom background + AI text with low opacity.
- Custom background + AI root background-color.
- Auto preset + AI text on noisy/dark background.

3. Tighten the LLM prompt for `attach_slide_html_to_plan`.

Required prompt rules:

- Root section must include safe padding.
- No root `width:1080px;height:1350px` without internal padding.
- No text opacity below `0.82`.
- No content pinned to `top:0`, `left:0`, `bottom:0`.
- For external background mode, do not use opaque full-screen backgrounds.

4. Decide product behavior for custom backgrounds.

Recommended rule:

- When user uploads a custom background, use it on every slide.
- AI may create panels, typography, and composition, but it must not replace the background image.

5. Keep preset backgrounds separate from custom backgrounds.

Required behavior:

- If `custom_background=True`, `preset_background_ids` must stay empty.
- Final user-facing summary should clearly say `Фон: свой загруженный`.
- Logs should include `custom_background=True` and slide count.

## Do Not Do

- Do not just increase text opacity globally without safe layout checks.
- Do not rely only on prompt wording; AI HTML must be normalized after generation.
- Do not disable custom backgrounds to hide the issue.
- Do not mix preset backgrounds into a custom-background generation.

