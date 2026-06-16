# Plan — Separate Test-Render Entry Point in Main Menu

**Status:** Draft → awaiting approval
**Track:** [./](./)

Each task is small enough to verify in one cycle.

---

## Task 1. Add the FSM state

**File:** `utils/states.py`

**What:** add a new `StatesGroup`:

```python
class TestRenderFlow(StatesGroup):
    waiting_for_text = State()
```

**Verify:** `rtk python -c "from utils.states import TestRenderFlow; print(TestRenderFlow.waiting_for_text.state)"`

**Done when:** import works and the state string is `TestRenderFlow:waiting_for_text`.

---

## Task 2. Add the menu button and command shortcut

**File:** `handlers/common.py`

**What:**
- Add a `🧪 Тестовый рендер` button in the main menu **for admin only**. Look for the existing menu keyboard builder (e.g. `_build_main_menu_keyboard` or similar) and conditionally add the button when `message.from_user.id == ADMIN_ID`.
- Register a `/test_render` command (admin only) that enters the FSM.

**Verify:** `rtk grep -n '🧪 Тестовый рендер\|test_render' handlers/common.py`

**Done when:** the button text and command appear in source, gated on `ADMIN_ID`.

---

## Task 3. Add the FSM handlers

**File:** `handlers/carousel_flow.py`

**What:** add a new section at the bottom (or a separate file) with:

- `cmd_test_render(message, state)` — sets `state.set_state(TestRenderFlow.waiting_for_text)`, sends the prompt.
- `test_render_text(message, state)` — handles text input: validates length, runs the LLM plan generation (same functions as `insta_auto`: `generate_instagram_carousel_plan`, `parse_carousel_plan`, `enforce_default_cta_slide`, `apply_theme_selection_policy`, `apply_theme_override`, `build_instagram_layout_specs`), stores `carousel_plan` and `layout_specs` in FSM data, and replies with the three style buttons.
- `test_render_voice(message, state, bot)` — handles voice input via the existing `transcribe_voice` helper (same pattern as `insta_auto`).
- `test_render_style_callback(callback, state)` — handles `test_render_style:<id>` callbacks, validates the style id against `STYLE_PRESETS`, retrieves plan/specs from FSM, renders, sends media group + caption, keeps the FSM state so the admin can pick another style.

The handlers live in the same router as `insta_auto` (or a new router; either works). Imports are added at the top of the file.

**Verify:**
- `rtk python -c "from handlers.carousel_flow import cmd_test_render, test_render_text, test_render_style_callback; print('ok')"`

**Done when:** all three handlers import cleanly and the callback prefix is `test_render_style:`.

---

## Task 4. Remove the three buttons from insta_auto result

**File:** `handlers/carousel_flow.py`

**What:** in `run_insta_auto_pipeline`, delete the two `action_rows.append(...)` lines that added the `🧪 Dark+Teal`, `🧪 Paper+Orange`, `🧪 White+Coral` buttons. Keep the publish/meta buttons intact.

**Verify:** `rtk grep -n 'Dark+Teal\|Paper+Orange\|White+Coral' handlers/carousel_flow.py` — the only remaining occurrences should be inside the new test-render handlers and inside `STYLE_PRESETS`.

**Done when:** the insta_auto result no longer contains the three test-render buttons.

---

## Task 5. Add flow-structure tests

**File:** `tests/test_flow_structure.py`

**What:** add:

- `test_test_render_menu_button_is_admin_only` — assert `"🧪 Тестовый рендер"` appears in `handlers/common.py`, inside the admin gate (similar pattern to `test_three_experimental_style_buttons_exist`).
- `test_test_render_command_handler_exists` — assert `async def cmd_test_render` and `TestRenderFlow` references exist.
- `test_test_render_style_callback_exists` — assert `test_render_style:` callback prefix is in source and the three style ids are referenced.
- `test_insta_auto_result_no_longer_has_test_render_buttons` — assert that `handlers/carousel_flow.py` does NOT contain the literal strings `"🧪 Dark+Teal"`, `"🧪 Paper+Orange"`, `"🧪 White+Coral"` in the `run_insta_auto_pipeline` function block. Implementation: find `run_insta_auto_pipeline`, find its end (next `@router.` or `def _build_experimental_export_package`), assert none of those three strings appear in the slice.

**Verify:** `rtk pytest tests/test_flow_structure.py -v`

**Done when:** the 4 new tests pass and existing tests stay green.

---

## Task 6. Full test suite + manual smoke

**What:**
- `rtk pytest tests/` — full suite must pass.
- Manual smoke (admin in Telegram): main menu → 🧪 Тестовый рендер → send text → tap all 3 styles → see 3 media groups. No new export-package rows in the DB.

**Verify:** `rtk pytest` returns 0 failures; smoke completes the loop.

**Done when:** full suite is green; smoke completes.

---

## Task 7. Final report + deploy

**What:** reply to the user with changed files, new UX, what was verified, and deploy to prod.

**Done when:** the user has all info to confirm the deploy worked.

---

## Out of Scope (explicit)

- Custom background upload in the test-render flow.
- Saving test renders as proper export packages.
- Touching `services/html_renderer.py` or `tests/test_html_renderer.py` (readability-fix).
- Touching `services/cover_renderer.py`.
- Auto-deploy (always explicit user approval).
