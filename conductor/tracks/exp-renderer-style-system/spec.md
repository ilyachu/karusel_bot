# Track: Experimental Renderer Style System + 3-Style Inline Preview

**Status:** Draft → awaiting approval
**Track ID:** `exp-renderer-style-system`
**Created:** 2026-06-16
**Owner:** conductor (planning phase)
**Depends on:** `experimental-carousel-pipeline` (must be merged/deployed first as a baseline; this track extends it)

---

## 1. Problem

The first version of the experimental carousel pipeline (track `experimental-carousel-pipeline`, shipped this session) has **one hardcoded visual style**: dark surface (`#0a0a0a`), system font stack, no accent, no background decoration. It is, by design, a control variable.

But the team wants the experimental renderer to actually **compete** with the production pipeline. To do that, the renderer must support the kind of design variation that real carousels have:

- Multiple **font families** (display, editorial, monospace, bold sans).
- Multiple **surfaces** (dark, paper, white, gradient, neon).
- An **accent color** for highlighted words — pulled from `LayoutSpec.highlight_words`, which already exists but is currently ignored.
- A **background decoration** (none, glow, dot grid, ruled lines).

Reference repositories reviewed:

- `DataTalksClub/carousel-automation` — Nunjucks templates + per-frame CSS, but only 4 frame types and a small palette.
- `itchernetski/threads-carousel-claude-skill` — a 4-axis style system: 5 fonts × 8 surfaces × 11 accents × 2 purposes = 880 combinations, 12 slide types, 8 background decorations, RU/EN toolbar. We borrow the **schema** and the **4-axis concept**, not the Next.js / React implementation.

The current experimental renderer is too minimal to A/B test meaningfully against the production pipeline.

## 2. Goal

Extend `services/experimental_carousel_renderer.py` to support a 4-axis style system inspired by `itchernetski/threads-carousel-claude-skill`, and replace the single "🧪 Тестовый рендер" button with **three inline-preview buttons** that each render the same carousel in a different preset style. The admin can then eyeball all three side-by-side.

The three preview styles (locked for v1):

| Label | Surface | Font | Accent | Background | Vibe |
|-------|---------|------|--------|------------|------|
| `🧪 Dark+Teal` | dark | clean (Inter) | teal | glow | tech / AI |
| `🧪 Paper+Orange` | paper | editorial (Playfair Display) | orange | ruled | журнал / блог |
| `🧪 White+Coral` | white | minimal (Unbounded) | coral | dots | editorial / bold |

Each style is a fixed composition of `(font, surface, accent, background)`. The schema is extensible — adding a 4th style is a one-line dict entry.

## 3. Non-Goals

- Expose all 880 combinations from `threads-carousel-claude-skill`. We ship **3** for v1; the architecture allows more later.
- Add Next.js, React, or any new runtime dependency. We stay Python + Playwright.
- Add a 5th slide type. The current 4 (hook / body / list / cta) stay; we do not introduce `quote` / `number` / `stats` / `checklist` in this track.
- Change production `services/html_renderer.py` or `tests/test_html_renderer.py` (uncommitted readability-fix stays).
- Auto-deploy.

## 4. UX

### New button rows in the "✅ Карусель готова" message

Replace the single "🧪 Тестовый рендер" button with three buttons, all gated by `ADMIN_ID`:

```text
[🧪 Dark+Teal]   callback_data = carousel_exp_render:<export_id>:dark_teal
[🧪 Paper+Orange]   callback_data = carousel_exp_render:<export_id>:paper_orange
[🧪 White+Coral]   callback_data = carousel_exp_render:<export_id>:white_coral
```

(Telegram inline keyboards wrap these into rows; we put them on a single row of 3 if Telegram allows, or 2+1 if not — see plan §Task 3 for the exact row layout.)

### User flow (per click)

1. Admin clicks, e.g., "🧪 Dark+Teal".
2. Bot removes the loading spinner on the button (`callback.answer()`).
3. Bot sends status: "🧪 Dark+Teal — рендерю…".
4. Bot renders the experimental PNGs for that style, saves a new export package with `render_mode="experimental-datatalks-dark_teal"` (note the style suffix), and sends them as a media group.
5. Bot sends a short caption: "🧪 Dark+Teal. Сравни с обычным и с другими пресетами.\n\nExport: <new_export_id>".
6. Bot updates the status to "✅ Dark+Teal готов."

The admin can click the other two buttons in sequence without re-generating the carousel. Each click produces a separate export package with its own `export_id`.

### Failure

Same as before: "⚠️ Dark+Teal не удался: <reason>." The production package and the other two experimental packages are unaffected.

## 5. Architecture

### 4-axis style schema (Python)

We define a small dataclass and three dicts at the top of `services/experimental_carousel_renderer.py`:

```python
@dataclass(frozen=True)
class StylePreset:
    id: str                                  # "dark_teal"
    label: str                               # "Dark+Teal"
    font_family: str                         # "Inter, system-ui, sans-serif"
    hook_font_family: str | None             # "Unbounded, ..."  or None
    surface_bg: str                          # "#0a0a0a" or "linear-gradient(...)"
    surface_text: str                        # "#f8fafc"
    surface_text_secondary: str              # "rgba(248,250,252,0.72)"
    accent_color: str                        # "#2dd4bf"
    background_css: str                      # see Backgrounds below
    purpose: str = "carousel"                # "carousel" or "presentation"
```

The three dicts follow the pattern from `itchernetski/threads-carousel-claude-skill`'s `presets.ts`:

```python
FONT_STYLES = {
    "minimal":   {"family": "Unbounded, system-ui, sans-serif",        "hook": "Unbounded, system-ui, sans-serif"},
    "editorial": {"family": "Playfair Display, Georgia, serif",        "hook": "Playfair Display, Georgia, serif"},
    "clean":     {"family": "Inter, system-ui, sans-serif",            "hook": "Inter, system-ui, sans-serif"},
    "mono":      {"family": "JetBrains Mono, Menlo, monospace",        "hook": "JetBrains Mono, Menlo, monospace"},
}

SURFACES = {
    "dark":   {"bg": "#0a0a0a",                 "text": "#f8fafc", "secondary": "rgba(248,250,252,0.72)"},
    "paper":  {"bg": "#f4ede0",                 "text": "#1a1815", "secondary": "rgba(26,24,21,0.62)"},
    "white":  {"bg": "#ffffff",                 "text": "#0a0a0a", "secondary": "rgba(10,10,10,0.62)"},
    # 'ember' and 'neon' are not exposed in v1 but the dicts hold them for future use.
}

ACCENTS = {
    "yellow": "#facc15",
    "teal":   "#2dd4bf",
    "orange": "#fb923c",
    "coral":  "#fb7185",
    "violet": "#a78bfa",
    "lime":   "#a3e635",
    "blue":   "#60a5fa",
}

BACKGROUNDS = {
    "none":   "",
    "glow":   "radial-gradient(circle at 30% 20%, {ACCENT_22}, transparent 60%)",
    "dots":   "background-image: radial-gradient(circle, {ACCENT_55} 1px, transparent 1px); background-size: 24px 24px;",
    "ruled":  "background-image: linear-gradient(180deg, transparent 79px, {ACCENT_22} 80px); background-size: 100% 80px;",
}

# The three presets shown to the admin.
STYLE_PRESETS = {
    "dark_teal": StylePreset(
        id="dark_teal",
        label="Dark+Teal",
        font_family=FONT_STYLES["clean"]["family"],
        hook_font_family=None,
        surface_bg=SURFACES["dark"]["bg"],
        surface_text=SURFACES["dark"]["text"],
        surface_text_secondary=SURFACES["dark"]["secondary"],
        accent_color=ACCENTS["teal"],
        background_css=BACKGROUNDS["glow"].replace("{ACCENT_22}", "rgba(45,212,191,0.18)").replace("{ACCENT_55}", "rgba(45,212,191,0.55)"),
    ),
    "paper_orange": StylePreset(
        id="paper_orange",
        label="Paper+Orange",
        font_family=FONT_STYLES["editorial"]["family"],
        hook_font_family=None,
        surface_bg=SURFACES["paper"]["bg"],
        surface_text=SURFACES["paper"]["text"],
        surface_text_secondary=SURFACES["paper"]["secondary"],
        accent_color=ACCENTS["orange"],
        background_css=BACKGROUNDS["ruled"].replace("{ACCENT_22}", "rgba(251,146,60,0.18)"),
    ),
    "white_coral": StylePreset(
        id="white_coral",
        label="White+Coral",
        font_family=FONT_STYLES["minimal"]["family"],
        hook_font_family=FONT_STYLES["minimal"]["hook"],
        surface_bg=SURFACES["white"]["bg"],
        surface_text=SURFACES["white"]["text"],
        surface_text_secondary=SURFACES["white"]["secondary"],
        accent_color=ACCENTS["coral"],
        background_css=BACKGROUNDS["dots"].replace("{ACCENT_55}", "rgba(251,113,133,0.55)"),
    ),
}
```

### HTML template changes

`build_experimental_slide_html(...)` gains a `style: StylePreset` parameter (defaulting to `STYLE_PRESETS["dark_teal"]` for back-compat with existing tests):

- `<link>` to Google Fonts: only the families that the chosen style needs (Inter / Playfair Display / Unbounded). Loaded via `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?...">`. **Same network dependency** that `services/html_renderer.py` already has for LAYOUT_STYLE_FONTS.
- `body` background switches from hardcoded `#0a0a0a` to `style.surface_bg` (or a `background-image: var(--bg-decoration), var(--surface-bg);` composition when `background_css` is non-empty).
- Text color switches to `style.surface_text`.
- Hook titles use `style.hook_font_family` if set, else `style.font_family`.
- The `highlight_words` from `LayoutSpec` are wrapped in `<span class="hl">` and styled with `style.accent_color`.
- For light surfaces (`paper`, `white`), the readability overlay over external backgrounds is reduced to a softer gradient (we keep readability, but we no longer assume dark mode).

### `map_layout_spec_to_experimental_slide` extension

`ExperimentalSlide` gains a `highlights: tuple[str, ...] = ()` field. The mapper copies `spec.highlight_words` into it. The HTML template splits `title` / `body` / `items` on whole-word occurrences of any highlight and wraps the matched substring in `<span class="hl">`.

### Renderer signature change

```python
def render_experimental_carousel(
    layout_specs: Sequence[LayoutSpec],
    logo_text: str = "chu ai",
    custom_background_data_url: str = "",
    preset_background_data_url: str = "",
    style: StylePreset | None = None,           # NEW
) -> list[bytes]:
```

Default `style=None` resolves to `STYLE_PRESETS["dark_teal"]` so the existing tests in `tests/test_experimental_carousel_renderer.py` keep working unchanged.

### Callback handler

`carousel_experimental_render` parses a 3-segment callback:

```text
carousel_exp_render:<export_id>:<style_id>
```

The existing 2-segment form (`carousel_exp_render:<export_id>`) is treated as `dark_teal` for back-compat — this is what we'll ship in the deploy script for any old button rows that may be cached client-side.

The handler reads `style_id`, looks up `STYLE_PRESETS[style_id]` (raises if unknown → user error → message), passes it into the render call, and the new export package is named `<export_dir>/...-<slug>-<style_id>` so admins can tell them apart on disk.

## 6. Files to Touch

| File | Change |
|------|--------|
| `services/experimental_carousel_renderer.py` | Add FONT_STYLES / SURFACES / ACCENTS / BACKGROUNDS / STYLE_PRESETS dicts. Add `StylePreset` dataclass. Extend `ExperimentalSlide.highlights`. Extend `map_layout_spec_to_experimental_slide(spec, style) -> ExperimentalSlide`. Extend `build_experimental_slide_html(slide, style, ...)`. Extend `render_experimental_carousel(..., style)`. |
| `handlers/carousel_flow.py` | Replace the single "🧪 Тестовый рендер" button with three buttons. Extend the callback handler to parse `<style_id>`. Extend `_build_experimental_export_package` to accept and propagate the style. |
| `tests/test_experimental_carousel_renderer.py` | Add tests for: 3 preset ids exist, each preset renders distinct HTML, `highlight_words` become `<span class="hl">`, light-surface readability over external bg, unknown `style_id` raises. Keep existing 18 tests passing (extend, do not delete). |
| `tests/test_flow_structure.py` | Add AST test that confirms all 3 button labels exist in source. Add AST test that confirms the callback handler parses a 3-segment form. |

## 7. Acceptance Criteria

1. All 18 existing tests in `tests/test_experimental_carousel_renderer.py` keep passing (default `style="dark_teal"`).
2. Three new buttons appear on the admin result: "🧪 Dark+Teal", "🧪 Paper+Orange", "🧪 White+Coral".
3. Each button produces a separate export package with `render_mode="experimental-datatalks-<style_id>"`.
4. Each style produces visually different HTML (asserts on `font-family`, surface color, accent color, background CSS).
5. `LayoutSpec.highlight_words` produces `<span class="hl">` markup that uses the style's `accent_color`.
6. Light surfaces (`paper`, `white`) still guarantee readable text over external backgrounds: a softer overlay + `text-shadow`.
7. Old 2-segment callback form `carousel_exp_render:<export_id>` resolves to `dark_teal` (back-compat).
8. Unknown `<style_id>` returns a friendly error to the user, never raises.
9. No production renderer or readability-fix change. No new runtime dependencies.
10. Full test suite (`rtk pytest tests/`) — 0 failures.
11. Manual smoke: render 3-slide carousel in all 3 styles; visually confirm fonts/colors/backgrounds differ.
12. The uncommitted readability changes in `services/html_renderer.py` and `tests/test_html_renderer.py` are not reverted.

## 8. Open Questions / Risks

- **Risk**: Google Fonts CDN may be blocked in the production container. Mitigation: fall back to system stack in HTML if `<link>` fails. We add a CSS rule `font-family: <system>, <google-font>, system-ui, ...` so the worst case is a system font, not a broken layout. This is the same pattern `services/html_renderer.py` uses.
- **Risk**: Light surface + custom photo background = weak readability. Mitigation: when `surface_bg` is light and `custom_background_data_url` is set, switch to a darker overlay (`rgba(7,10,18,0.62) → 0.76`) instead of the default light overlay. The track spec locks this rule.
- **Risk**: 3 styles × 3-5 slides × Playwright launch = noticeable wait (potentially 20-30s for a 3-style run). Mitigation: each button click renders **one** style only, not all three. The admin clicks three times if they want all three.
- **Risk**: 3 buttons on one Telegram row may overflow. Mitigation: layout is `[[Dark+Teal, Paper+Orange], [White+Coral]]` (2+1) on narrow clients; Telegram will wrap automatically.
- **Risk**: New export packages accumulate on disk. Mitigation: out of scope for this track; admin can clean manually.

## 9. Reference Repos

- `DataTalksClub/carousel-automation` — pipeline pattern (taken in track 1).
- `itchernetski/threads-carousel-claude-skill` — 4-axis style system, `presets.ts` shape, font/surface/accent composition. We borrow **schema**, not implementation.
