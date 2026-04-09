## Implementation Journey

### Goal

Turn the Telegram carousel bot into a production-ready `Insta Auto` generator:
`text -> publish-ready carousel -> caption -> export package -> future Instagram publishing`.

### What was done

#### Phase 1: Foundation

- cleaned runtime hygiene
- moved logs/data behind env-configured paths
- removed local DB/log artifacts from git
- introduced tests for renderer and admin/data logic
- upgraded the Pillow renderer from a rigid overlay to an adaptive transition layout engine

Key files:
- `services/image_renderer.py`
- `config.py`
- `main.py`
- `utils/database.py`

#### Phase 2: Instagram-ready output

- added `🚀 Insta Auto`
- generated Instagram-ready carousels with minimal interaction
- added caption generation
- added export packages with slides, caption, and metadata

Key files:
- `handlers/carousel_flow.py`
- `services/gemini_client.py`
- `services/instagram_package.py`

#### Phase 3: Rich renderer

- added an HTML/CSS renderer via Playwright for `Insta Auto`
- preserved Pillow as a fallback renderer
- made `Insta Auto` the only path using the new HTML renderer

Key files:
- `services/html_renderer.py`
- `Dockerfile`
- `requirements.txt`

#### Phase 4: Meaning-first layout

- introduced `carousel plan -> layout specs -> render`
- added slide roles, density, theme hints, and supporting cards
- persisted plan/layout metadata into export packages

Key files:
- `services/layout_engine.py`
- `services/gemini_client.py`
- `handlers/carousel_flow.py`

#### Phase 5: Visual systems

- added reusable themes:
  - `memory_archive`
  - `founder_brief`
  - `growth_black`
  - `research_mono`
- refined supporting-card count by slide role instead of fixed counts

### Current architecture

1. User sends text / voice / forwarded post.
2. Gemini produces an Instagram carousel plan.
3. Theme selection policy validates or overrides the proposed theme.
4. Layout engine converts the carousel plan into layout specs.
5. HTML renderer renders each slide.
6. Export package stores:
   - slide PNGs
   - caption
   - metadata
   - carousel plan
   - layout specs
   - theme decision

### Theme selection policy

Theme selection is no longer left entirely to the model.

Current flow:
- model proposes `theme_hint`
- local policy scores themes from lexical/content signals
- final theme is selected deterministically
- the decision is stored in export metadata

This makes the system more stable for recurring post types like:
- growth
- founder/product
- research/framework
- memory/knowledge

### What remains

- visual QA across more real posts
- stronger theme-specific compositions
- optional theme chooser or override in Telegram
- Meta publishing layer on top of export packages
