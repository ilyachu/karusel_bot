# Track: Style Options in Test-Render FSM

**Status:** Draft → awaiting approval
**Track ID:** `test-render-style-options`
**Created:** 2026-06-16
**Owner:** conductor (planning phase)
**Depends on:** `test-render-entry-point` (must be deployed as baseline)

---

## 1. Problem

The test-render entry point (track `test-render-entry-point`) currently has a one-shot flow:
1. Admin taps the "🧪 Тестовый рендер" button.
2. Bot asks for text.
3. Admin sends text.
4. Bot generates a `carousel_plan` and shows 3 style buttons.

There is no step where the admin can choose **how the text is rewritten** before the plan is generated. The previous `insta_auto` flow exposes this as the "Подача текста" choice (`exact / concise / educational / marketing` → "Как есть / Короче / Подробнее / Ярче"). For the test-render flow, the admin has no control over this — the plan is generated with a hard-coded `concise`.

For a real A/B test of visual styles, the admin must also be able to **vary the textual content** (not only the visual style). Otherwise the experiment is only half-controlled.

## 2. Goal

Insert one extra state in the test-render mini-FSM between "text received" and "plan generated":

1. Admin taps "🧪 Тестовый рендер".
2. Bot: "Пришли текст".
3. Admin sends text.
4. Bot shows a small inline keyboard: «Как есть / Короче / Подробнее / Ярче» (4 options, mapped to `exact / concise / educational / marketing`).
5. Admin taps one of the 4 rewrite styles.
6. Bot generates a `carousel_plan` using the chosen rewrite style.
7. Bot shows the 3 visual style buttons (`Dark+Teal / Paper+Orange / White+Coral`).
8. Admin taps a visual style.
9. Bot renders, sends media group, keeps the visual-style buttons.

The `exact` (Как есть) option means: do not rewrite the text. The LLM still gets called for the carousel plan, but the rewrite_style="exact" hint tells the model to preserve the user's original text.

The production `insta_auto` flow is **not touched**. We **re-use** the existing `INSTA_REWRITE_LABELS` mapping in `handlers/common.py` and the existing `insta_copy:` callback handler **in a scoped way** (only the test-render FSM states trigger it).

## 3. Non-Goals

- Adding more rewrite options beyond the existing 4.
- Adding a separate color/visual_mode picker (we have 3 visual style presets, that is enough for the experiment).
- Persisting the admin's choice of rewrite style across test-render sessions (it resets on /start).
- Touching `insta_auto` or any production logic.
- Touching `services/html_renderer.py` or `tests/test_html_renderer.py` (readability-fix preserved).

## 4. UX

### New state

Add to `utils/states.py`:

```python
class TestRenderFlow(StatesGroup):
    waiting_for_text = State()       # admin sent /test_render, bot awaits text
    waiting_for_rewrite = State()    # admin sent text, bot shows 4 rewrite buttons
    waiting_for_style = State()      # admin chose rewrite, bot awaits visual style
```

### Flow

1. Admin taps "🧪 Тестовый рендер" → state = `waiting_for_text`. Bot: "🧪 Тестовый рендер. Пришли текст…".
2. Admin sends text → state = `waiting_for_rewrite`. Bot: "🧪 Выбери, как обработать текст:" + 4 inline buttons:
   ```
   [Как есть] [Короче]
   [Подробнее] [Ярче]
   ```
3. Admin taps one of the 4 → state = `waiting_for_style`. Bot: "🧪 Готовлю план в режиме «<label>»…".
4. Bot generates the plan with `rewrite_style=<choice>` and shows the 3 visual style buttons.
5. Admin taps a visual style → bot renders, sends PNG, keeps visual style buttons.
6. Admin can tap another visual style (without re-choosing rewrite) or send new text (resets to step 1).
7. Admin can press /start at any time to leave the FSM (existing behavior).

### Error states

- Empty text → "🧪 Пришли непустой текст." (existing).
- Voice transcription failure → existing.
- LLM plan failure → "⚠️ Не удалось сгенерировать план: <reason>." + state = `waiting_for_rewrite` so the admin can re-pick rewrite style.
- Unknown rewrite style in callback → "⚠️ Неизвестный режим текста: <id>." + state = `waiting_for_rewrite`.

## 5. Architecture

### Files to modify

| File | Change |
|------|--------|
| `utils/states.py` | + `TestRenderFlow.waiting_for_rewrite` state. |
| `handlers/carousel_flow.py` | + inline keyboard constant `_TEST_RENDER_REWRITE_ROW`. `test_render_text` and `test_render_voice` now set state to `waiting_for_rewrite` (not `waiting_for_style`) and show the rewrite keyboard. + new handler `test_render_rewrite_callback` (gated by `waiting_for_rewrite`) that triggers plan generation with the chosen `rewrite_style` and shows the visual style buttons. `test_render_style_callback` is gated by `waiting_for_style` (existing). `_generate_test_render_plan(text, rewrite_style)` takes a new `rewrite_style` parameter. |
| `handlers/common.py` | No change. We re-use `INSTA_REWRITE_LABELS` and **scope** the existing `insta_copy_selected` handler to also accept `TestRenderFlow.waiting_for_rewrite` as a valid state (extend `StateFilter`). |
| `tests/test_flow_structure.py` | + AST tests: 4 rewrite labels exist; the `insta_copy:` callback is reachable from `TestRenderFlow.waiting_for_rewrite`; `_TEST_RENDER_REWRITE_ROW` exists; `test_render_text` transitions to `waiting_for_rewrite`. |
| `services/html_renderer.py`, `tests/test_html_renderer.py` | NOT touched. |

### State diagram

```
                    /start, /test_render
                              |
                              v
        +-----------------------------------------+
        |     TestRenderFlow.waiting_for_text     |
        +-----------------------------------------+
              |                          ^
       text/voice                  /start
              v                          |
        +-----------------------------------------+
        |   TestRenderFlow.waiting_for_rewrite   |
        +-----------------------------------------+
              |   cancel            |
              v                      |
       LLM plan generation
              v
        +-----------------------------------------+
        |     TestRenderFlow.waiting_for_style    |
        +-----------------------------------------+
              |   new text   /start
              v
        (back to waiting_for_text)
```

### Plan generation

`_generate_test_render_plan(text, rewrite_style)` passes `rewrite_style` to `generate_instagram_carousel_plan(...)`. The existing `insta_auto` flow already does this (see `handlers/carousel_flow.py` line 287).

## 6. Acceptance Criteria

1. After sending text, the bot shows 4 inline buttons «Как есть / Короче / Подробнее / Ярче» instead of jumping straight to the plan.
2. Tapping one of the 4 buttons generates a plan and shows the 3 visual style buttons.
3. The plan is actually generated with the chosen `rewrite_style`: when the admin taps "Как есть", the slide texts are very close to the original input; when the admin taps "Ярче", the slide texts are punchier.
4. The 3 visual style buttons work the same as before.
5. The existing `insta_auto` flow is unchanged.
6. `services/html_renderer.py` and `tests/test_html_renderer.py` are not modified.
7. All existing tests pass; new AST tests pass.
8. Manual smoke: full flow works in Telegram (text → rewrite choice → plan → style choice → PNG).

## 7. Open Questions / Risks

- **Risk**: The `insta_copy:` callback is also handled by `insta_copy_selected` in `handlers/common.py`, which is currently scoped to `CarouselFlow.insta_auto_waiting_for_text` and `insta_auto_waiting_for_background`. If we just add `TestRenderFlow.waiting_for_rewrite` to the `StateFilter`, the same callback handler can be reused — but it calls `show_insta_auto_setup` which is the wrong UX for test-render. Mitigation: write a new callback handler `test_render_rewrite_callback` (gated by `TestRenderFlow.waiting_for_rewrite`) with the same callback prefix `insta_copy:` but different post-action (generates the test-render plan instead of going back to setup). This way, the FSM state decides which handler runs.
- **Risk**: When the admin picks a rewrite, we still call the LLM. If the LLM is slow (currently 30-60s on `neuraldeep.ru`), the user sees another "Готовлю план…" status. Acceptable, same latency as production.
- **Risk**: `exact` mode may cause the LLM to produce a plan with very long slide bodies. This is the same as production `insta_auto` with `exact` — already handled by `validate_text_length`.

## 8. Reference

- Track `test-render-entry-point` for the FSM state machine to extend.
- `handlers/common.py::INSTA_REWRITE_LABELS` and `insta_copy_selected` for the source of truth on rewrite style labels.
- `handlers/carousel_flow.py::run_insta_auto_pipeline` for the existing plan-generation pattern.
