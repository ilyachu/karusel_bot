# Track: Separate Test-Render Entry Point in Main Menu

**Status:** Draft → awaiting approval
**Track ID:** `test-render-entry-point`
**Created:** 2026-06-16
**Owner:** conductor (planning phase)
**Depends on:** `exp-renderer-style-system` (must be deployed as baseline)

---

## 1. Problem

In the current design (after tracks `experimental-carousel-pipeline` and `exp-renderer-style-system`), the only way to trigger the experimental renderer is from the bottom of the production carousel result message — three inline buttons `🧪 Dark+Teal / 🧪 Paper+Orange / 🧪 White+Coral` are appended to the "✅ Карусель готова" message.

This means to test the experimental renderer the admin has to:
1. Run the full `insta_auto` production pipeline (LLM plan + production render + media group + caption).
2. Wait for the production PNGs to be sent.
3. Click one of the three test buttons in the resulting message.

For an **iterative** style test (e.g. trying 3 styles on 4 different texts in a row), this is wasteful and slow. The production render is not the goal; it is just a step in the way to the experimental renderer.

The team wants a **faster loop**: enter the experimental pipeline directly, skip the production render, and iterate quickly between text and style.

## 2. Goal

Add a **separate entry point** in the bot's main menu called "🧪 Тестовый рендер" that opens a small FSM:

1. Admin opens the main menu (or types `/test_render`).
2. Taps "🧪 Тестовый рендер".
3. Bot asks for the source text (or voice message).
4. Admin sends text.
5. Bot generates a `carousel_plan` via the same LLM pipeline as `insta_auto`, but does **not** run the production renderer and does **not** save a production export.
6. Bot replies with three inline buttons: `🧪 Dark+Teal`, `🧪 Paper+Orange`, `🧪 White+Coral`.
7. Admin taps a style.
8. Bot renders the experimental slides in that style and sends them as a media group, with caption "🧪 <style>. Тестовый рендер."
9. Bot offers the other two style buttons again, so the admin can re-render the same content in a different style without re-sending text.

The production pipeline (`insta_auto`) is **not touched**. The 3 inline buttons in the production result message are **removed** to avoid confusion (the test-render flow is now the single, dedicated place for experimental rendering).

## 3. Non-Goals

- Persist test renders to the export-packages database or save them to disk as proper export packages. v1 keeps test renders ephemeral: PNGs are sent, then discarded.
- Add cover generation or admin publishing logic to the test-render flow.
- Support uploading a custom background photo in v1 (presets are still not persisted; custom bg remains a v2 concern).
- Replace the production renderer.
- Touch `services/html_renderer.py` or `tests/test_html_renderer.py` (uncommitted readability-fix stays).
- Auto-deploy.

## 4. UX

### Main menu addition

In `handlers/common.py`, the main menu already exposes `📬 Обратная связь` and (presumably) `📸 Создать карусель` / `🧪 Тестовый рендер` candidates. We add a new menu button:

```text
🧪 Тестовый рендер
```

for admin users only (gate `ADMIN_ID`). Tapping it triggers the new FSM.

A text shortcut `/test_render` is also registered for admins who prefer commands.

### FSM states

Add to `utils/states.py`:

```python
class TestRenderFlow(StatesGroup):
    waiting_for_text = State()  # admin sent /test_render, bot awaits text/voice
```

### Flow

1. Admin taps `🧪 Тестовый рендер` (or `/test_render`).
2. Bot: "🧪 Тестовый рендер. Пришли текст для карусели (или голосовое сообщение). Я сгенерирую план и покажу превью 3 стилей."
3. Admin sends text (or voice → transcribed by OpenAI speech).
4. Bot runs the LLM plan generation:
   - `validate_text_length(text)`
   - `resolve_target_slide_count(text, "auto")` (or the existing setup, kept identical to `insta_auto`)
   - `generate_instagram_carousel_plan(...)`
   - `parse_carousel_plan(raw_plan)`
   - `enforce_default_cta_slide(plan, ...)`
   - `apply_theme_selection_policy(...)`
   - `apply_theme_override(...)`
   - `build_instagram_layout_specs(plan, ...)`
5. Bot replies with a status message "🧪 План готов. Выбери стиль:" + three inline buttons:
   ```text
   [🧪 Dark+Teal]   callback_data = test_render_style:dark_teal
   [🧪 Paper+Orange] callback_data = test_render_style:paper_orange
   [🧪 White+Coral]  callback_data = test_render_style:white_coral
   ```
6. The chosen style's data URL is set to `""` (no custom background in v1).
7. Admin taps a style.
8. Bot answers the callback (silent).
9. Bot edits the status message: "🧪 <style> — рендерю…".
10. Bot renders the experimental PNGs via `render_experimental_carousel(layout_specs, style=preset)`.
11. Bot sends a media group with the PNGs.
12. Bot sends a short caption: "🧪 <style>. Тестовый рендер. Прогоняй тот же текст через другие стили."
13. Bot edits the status to: "✅ <style> готов. Выбери другой стиль или пришли новый текст."
14. The state is kept in `waiting_for_text` so a new text immediately starts a new plan; the three style buttons are also re-shown on every render so the admin can keep iterating without leaving the FSM.

### Failure

- If the LLM call fails: bot sends "⚠️ Не удалось сгенерировать план: <reason>." and stays in the FSM, so admin can re-send text.
- If Playwright fails for a particular style: Pillow fallback kicks in (already in `render_experimental_carousel`); the admin still gets PNGs. The status message is edited to "✅ <style> готов (fallback)."
- If admin sends non-text (sticker, photo, etc.) while in the FSM: bot sends "🧪 Пришли текст или голосовое сообщение." and stays in the FSM.

## 5. Architecture

### Files to create

None beyond test files.

### Files to modify

| File | Change |
|------|--------|
| `utils/states.py` | Add `TestRenderFlow(StatesGroup)` with `waiting_for_text` state. |
| `handlers/common.py` | Add a `🧪 Тестовый рендер` button in the main menu for admin (and a `/test_render` command shortcut). |
| `handlers/carousel_flow.py` | Add a small router section: `cmd_test_render`, `test_render_text`, `test_render_voice`, `test_render_style_callback`. These do not touch the existing insta_auto flow. **Remove the three test-render inline buttons from the insta_auto result message** (lines ~520-528). |
| `tests/test_flow_structure.py` | Add AST tests confirming the new menu button, command, and callback; and that the insta_auto result no longer contains the three test-render buttons. |
| `tests/test_html_renderer.py` / `services/html_renderer.py` | NOT touched. |

### Persistence

The test-render flow does **not** create an export package. It does **not** call `build_instagram_export` or `save_export_package`. The state is held in `FSMContext` only. The PNGs are built in memory, sent, then discarded.

### State cleanup

`FSMContext.clear()` is called on `/start` or on `cmd_cancel`, as the existing insta_auto flow does. We do not introduce a separate cancel command.

## 6. Acceptance Criteria

1. Production `insta_auto` flow is unchanged: it still produces the same result, the same publish buttons, the same caption. **Only** the three experimental-render buttons are removed from the "✅ Карусель готова" message.
2. A new `🧪 Тестовый рендер` button is visible in the bot's main menu for admin (and only admin).
3. Tapping the button starts a new FSM. Tapping it as a non-admin does nothing visible (or shows a "только для админа" message — implementation choice).
4. Sending text produces a `carousel_plan`, after which three style buttons appear.
5. Tapping a style renders the carousel in that style and sends the PNGs as a media group. No new export package is created (verifiable by counting rows in `export_packages`).
6. After the render, the same three style buttons are still available so the admin can re-render in another style without re-sending text.
7. Sending a new text replaces the plan (a new plan + new style buttons).
8. The readability-fix in `services/html_renderer.py` and the new experimental renderer are untouched.
9. All existing tests in `tests/` keep passing; new flow-structure tests pass.
10. Manual smoke: complete the loop in Telegram as admin: open menu → tap test-render → send text → tap all 3 styles → see 3 media groups. The export_packages table row count does not increase.

## 7. Open Questions / Risks

- **Risk**: The LLM plan takes 5–10 seconds; if the admin impatiently taps a style button before the plan is ready, the callback may fire on stale state. Mitigation: the style callback handler only fires after the plan is in `FSMContext`. If the plan is missing, it sends "🧪 Сначала пришли текст" and returns.
- **Risk**: Reusing the same LLM for the test pipeline ties it to the same latency/cost as `insta_auto`. Acceptable: this is the same model and we just skip the production render, which is cheap.
- **Risk**: Some users may not see the new button until they refresh the menu. Mitigation: send a "menu updated" hint on first deploy if necessary. Out of scope.
- **Risk**: Sending PNGs without saving them loses the test result if the admin wants to revisit. Mitigation: v1 accepts this; v2 could add an opt-in "save as export" toggle.

## 8. Reference

- Tracks 1 & 2 (`experimental-carousel-pipeline`, `exp-renderer-style-system`) for the renderer that this track wraps in a friendlier entry point.
- `handlers/common.py` for the main-menu button style and the `Feedback` pattern (state in `StatesGroup`, button in keyboard, `router.message` handler).
