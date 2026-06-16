# Plan — Style Options in Test-Render FSM

**Status:** Draft → awaiting approval
**Track:** [./](./)

---

## Task 1. Add the new state

**File:** `utils/states.py`

**What:** add `TestRenderFlow.waiting_for_rewrite = State()`.

**Verify:** `rtk python -c "from utils.states import TestRenderFlow; print(TestRenderFlow.waiting_for_rewrite.state)"` → `TestRenderFlow:waiting_for_rewrite`.

**Done when:** import works.

---

## Task 2. Add the rewrite-style keyboard constant and refactor plan generation

**File:** `handlers/carousel_flow.py`

**What:**
- Add a module-level constant `_TEST_RENDER_REWRITE_ROW = [[InlineKeyboardButton(text="<label>", callback_data=f"insta_copy:{key}"), ...]]` with the 4 rewrite options from `INSTA_REWRITE_LABELS` (use the existing `handlers.common.INSTA_REWRITE_LABELS` dict).
- Change `_generate_test_render_plan(text)` to `_generate_test_render_plan(text, rewrite_style)`. Pass `rewrite_style` into `generate_instagram_carousel_plan(...)` and into `build_fallback_instagram_plan` (the latter takes no `rewrite_style`, so no change there).
- In `test_render_text`: after validating text, do **not** generate the plan. Instead, set state to `waiting_for_rewrite` and show the rewrite keyboard.
- Same for `test_render_voice`.

**Verify:** `rtk python -c "from handlers.carousel_flow import _generate_test_render_plan, _TEST_RENDER_REWRITE_ROW; print('ok')"`

**Done when:** import works; the rewrite row has 4 buttons.

---

## Task 3. Add the rewrite-style callback handler

**File:** `handlers/carousel_flow.py`

**What:** add a new handler `test_render_rewrite_callback(callback, state)`:

- gated by `TestRenderFlow.waiting_for_rewrite` and `F.data.startswith("insta_copy:")`
- reads the rewrite key, validates it against `INSTA_REWRITE_LABELS` (imported from `handlers.common`)
- if invalid: sends a friendly error and stays in the same state
- if valid: edits the status to "🧪 Готовлю план в режиме «<label>»…", generates the plan with that `rewrite_style`, stores the result in FSM data, sets state to `waiting_for_style`, shows the 3 visual style buttons.

**Verify:** `rtk python -c "from handlers.carousel_flow import test_render_rewrite_callback; print('ok')"`

**Done when:** the handler is importable and uses the right state.

---

## Task 4. Update `test_render_style_callback` to require the new state

**File:** `handlers/carousel_flow.py`

**What:** the existing `test_render_style_callback` is currently gated by `TestRenderFlow.waiting_for_style`. That's already correct. Confirm and add a guard test.

**Verify:** `rtk grep "F.data.startswith(\"test_render_style:")" handlers/carousel_flow.py`

**Done when:** the gate is `TestRenderFlow.waiting_for_style`.

---

## Task 5. Add flow-structure tests

**File:** `tests/test_flow_structure.py`

**What:** add:

- `test_test_render_rewrite_keyboard_has_four_options` — assert that `_TEST_RENDER_REWRITE_ROW` exists and contains 4 buttons with the labels «Как есть», «Короче», «Подробнее», «Ярче».
- `test_test_render_rewrite_callback_handler_exists` — assert that `async def test_render_rewrite_callback` exists and uses `F.data.startswith("insta_copy:")`.
- `test_test_render_text_transitions_to_rewrite_state` — assert that `test_render_text` and `test_render_voice` both call `state.set_state(TestRenderFlow.waiting_for_rewrite)`.
- `test_test_render_state_machine_has_three_states` — assert `TestRenderFlow.waiting_for_rewrite.state` exists.

**Verify:** `rtk pytest tests/test_flow_structure.py -v`

**Done when:** the new tests pass and existing tests stay green.

---

## Task 6. Full test suite + manual smoke

**What:**
- `rtk pytest tests/` — full suite must pass.
- Manual smoke: tap "🧪 Тестовый рендер" → send text → tap «Как есть» → tap «Dark+Teal» → see PNG. Repeat with «Ярче» to confirm the rewrite actually changes the text.

**Verify:** `rtk pytest` returns 0 failures.

**Done when:** full suite is green.

---

## Task 7. Final report + commit + deploy

**What:** commit + push + `down + up -d --build` (the only deploy command that actually applies code per `workflow.md`).

**Done when:** the user can test in Telegram.

---

## Out of Scope (explicit)

- Adding a color/visual_mode picker (we have 3 visual style presets, enough for v1).
- Persisting admin's rewrite choice across test-render sessions.
- Touching `insta_auto` or any production logic.
- Touching `services/html_renderer.py` or `tests/test_html_renderer.py`.
