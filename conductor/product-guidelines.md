# Product Guidelines — karusel_bot

## Audience & Language

- Russian-first. All user-facing copy, labels, and button text in Russian.
- Tone: confident, practical, opinionated. No hype.

## Visual Identity

- 1080x1350 portrait slides (Instagram feed).
- Dark surface as the default; light surface only when no external background is present.
- Readability is non-negotiable: any text over an image background must pass contrast.

## Feature Surface Discipline

- New visual paths are added as **opt-in experiments**, not as replacements.
- Every new render path keeps the existing production path working unchanged until the experiment is verified.
- Buttons and labels are short, in Russian, with at most one emoji prefix.

## Code & Module Boundaries

- New renderers go in `services/`, not `handlers/`.
- Render functions are pure and synchronous; handlers call them via `asyncio.to_thread(...)`.
- Schema mapping between pipeline types (e.g. `LayoutSpec → ExperimentalSlide`) lives in the renderer module, not in `layout_engine.py`, to keep the experimental path isolated.

## Failure Modes

- A failed experimental render must never break the production carousel generation.
- Experimental render failures log a warning and send a short Telegram message — they do not raise.
