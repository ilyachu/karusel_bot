import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FlowStructureTests(unittest.TestCase):
    def test_carousel_flow_has_no_duplicate_function_names(self):
        source = (PROJECT_ROOT / "handlers" / "carousel_flow.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        function_names = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        duplicates = sorted(
            {
                name
                for name in function_names
                if function_names.count(name) > 1
            }
        )

        self.assertEqual(duplicates, [])

    def test_carousel_flow_has_no_manual_pipeline(self):
        source = (PROJECT_ROOT / "handlers" / "carousel_flow.py").read_text(encoding="utf-8")

        self.assertNotIn("async def ask_standard_visual_method", source)
        self.assertNotIn("async def process_text_input", source)
        self.assertNotIn("async def generate_carousel", source)
        self.assertNotIn("async def _generate_template_carousel", source)
        self.assertNotIn("choosing_slide_count", source)
        self.assertNotIn("choosing_rewrite_style", source)

    def test_feedback_button_is_in_main_menu(self):
        source = (PROJECT_ROOT / "handlers" / "common.py").read_text(encoding="utf-8")
        self.assertIn('KeyboardButton(text="📬 Обратная связь")', source)

    def test_feedback_state_exists(self):
        from handlers.common import Feedback
        self.assertEqual(Feedback.waiting_for_message.state, "Feedback:waiting_for_message")

    def test_feedback_handler_forwards_to_admin(self):
        source = (PROJECT_ROOT / "handlers" / "common.py").read_text(encoding="utf-8")
        self.assertIn("async def cmd_feedback_start", source)
        self.assertIn("async def cmd_feedback_receive", source)
        self.assertIn("bot.send_message(ADMIN_ID", source)

    def test_access_middleware_allows_feedback_for_all(self):
        source = (PROJECT_ROOT / "middlewares" / "access.py").read_text(encoding="utf-8")
        self.assertIn("Feedback.waiting_for_message", source)
        self.assertIn("current_state == Feedback.waiting_for_message", source)

    def test_create_carousel_uses_insta_auto_setup(self):
        source = (PROJECT_ROOT / "handlers" / "common.py").read_text(encoding="utf-8")

        self.assertIn("async def start_insta_creation_setup", source)
        self.assertIn("async def cmd_insta_auto", source)
        self.assertIn("start_insta_creation_setup(", source)

    def test_insta_auto_style_packs_are_product_facing(self):
        from handlers.common import (
            INSTA_COLOR_LABELS,
            INSTA_REWRITE_LABELS,
            INSTA_SLIDE_COUNT_LABELS,
        )

        self.assertIn("exact", INSTA_REWRITE_LABELS)
        self.assertIn("concise", INSTA_REWRITE_LABELS)
        self.assertIn("educational", INSTA_REWRITE_LABELS)
        self.assertIn("marketing", INSTA_REWRITE_LABELS)
        self.assertIn("dark", INSTA_COLOR_LABELS)
        self.assertIn("light", INSTA_COLOR_LABELS)
        self.assertIn("warm", INSTA_COLOR_LABELS)
        self.assertIn("bold", INSTA_COLOR_LABELS)
        self.assertEqual(INSTA_SLIDE_COUNT_LABELS["auto"], "Авто")
        self.assertEqual(INSTA_SLIDE_COUNT_LABELS["7"], "7")

    def test_insta_setup_exposes_slide_count_and_background_mode(self):
        from handlers.common import _build_insta_setup_keyboard, _insta_setup_summary

        data = {
            "insta_slide_count": "6",
            "insta_custom_bg_bytes": b"demo",
        }

        summary = _insta_setup_summary(data)
        keyboard = _build_insta_setup_keyboard(data)
        callback_ids = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data
        ]

        self.assertIn("Слайды: 6", summary)
        self.assertIn("Фон: свой загружен", summary)
        self.assertIn("insta_slides:auto", callback_ids)
        self.assertIn("insta_slides:4", callback_ids)
        self.assertIn("insta_slides:7", callback_ids)

    def test_target_slide_count_can_be_forced_from_setup(self):
        from handlers.common import resolve_target_slide_count

        short_text = "Короткий текст для проверки ручного числа слайдов."

        self.assertEqual(resolve_target_slide_count(short_text, "6"), 6)
        self.assertEqual(resolve_target_slide_count(short_text, "auto"), 4)

    def test_pipeline_progress_text_is_staged(self):
        from handlers.carousel_flow import _build_pipeline_status

        status = _build_pipeline_status(2, 5, "Собираю структуру", "Слайды и порядок блоков")

        self.assertIn("Шаг 2/5", status)
        self.assertIn("Собираю структуру", status)

    def test_carousel_logo_uses_user_id_not_chat_id(self):
        from handlers.carousel_flow import _resolve_user_logo_for_message

        message = SimpleNamespace(
            from_user=SimpleNamespace(id=123),
            chat=SimpleNamespace(id=-100987),
        )

        with patch("handlers.carousel_flow.get_user_logo", return_value="brand") as mocked:
            self.assertEqual(_resolve_user_logo_for_message(message), "brand")

        mocked.assert_called_once_with(123)

    def test_carousel_logo_falls_back_to_chat_id_without_user(self):
        from handlers.carousel_flow import _resolve_user_logo_for_message

        message = SimpleNamespace(
            from_user=None,
            chat=SimpleNamespace(id=456),
        )

        with patch("handlers.carousel_flow.get_user_logo", return_value="chat-brand") as mocked:
            self.assertEqual(_resolve_user_logo_for_message(message), "chat-brand")

        mocked.assert_called_once_with(456)

    def test_logo_settings_accept_text_only(self):
        source = (PROJECT_ROOT / "handlers" / "common.py").read_text(encoding="utf-8")

        self.assertIn("@router.message(Settings.waiting_for_logo, F.text)", source)
        self.assertIn("async def settings_logo_wrong_input", source)

    def test_cover_flow_uses_user_logo(self):
        source = (PROJECT_ROOT / "handlers" / "cover_flow.py").read_text(encoding="utf-8")

        self.assertIn("from utils.database import get_user_logo", source)
        self.assertIn("_resolve_user_logo_for_cover_event", source)
        self.assertIn('raw_plan["footer_right"] = user_logo', source)
        self.assertIn("Автор: {plan.footer_right}", source)
        self.assertNotIn("Автор: chu_il", source)

    def test_cover_flow_exposes_text_mode_step(self):
        source = (PROJECT_ROOT / "handlers" / "cover_flow.py").read_text(encoding="utf-8")
        states_source = (PROJECT_ROOT / "utils" / "states.py").read_text(encoding="utf-8")

        self.assertIn("cover_choosing_text_mode", states_source)
        self.assertIn("COVER_TEXT_MODE_LABELS", source)
        self.assertIn("cover_text_mode:exact", source)
        self.assertIn("cover_text_mode:marketing", source)
        self.assertIn("cover_text_mode:educational", source)
        self.assertIn("cover_text_mode:concise", source)
        self.assertIn("cover_text_mode=text_mode", source)
        self.assertIn("generate_cover_plan(base_text, style, format_key, text_mode)", source)
        self.assertIn("Текст: {COVER_TEXT_MODE_LABELS.get(text_mode", source)

    def test_cover_text_mode_keyboard_contains_product_labels(self):
        from handlers.cover_flow import COVER_TEXT_MODE_LABELS, _text_mode_keyboard

        keyboard = _text_mode_keyboard()
        labels = [
            button.text
            for row in keyboard.inline_keyboard
            for button in row
        ]

        self.assertEqual(COVER_TEXT_MODE_LABELS["exact"], "Сохранить исходный")
        self.assertEqual(COVER_TEXT_MODE_LABELS["marketing"], "Продающий")
        self.assertEqual(COVER_TEXT_MODE_LABELS["educational"], "Обучающий")
        self.assertEqual(COVER_TEXT_MODE_LABELS["concise"], "Кратко суть")
        self.assertIn("Сохранить исходный", labels)
        self.assertIn("Продающий", labels)
        self.assertIn("Обучающий", labels)
        self.assertIn("Кратко суть", labels)

    def test_cover_plan_prompt_accepts_text_mode(self):
        source = (PROJECT_ROOT / "services" / "gemini_client.py").read_text(encoding="utf-8")

        self.assertIn('generate_cover_plan(base_text: str, style: str, format_key: str, text_mode: str = "concise")', source)
        self.assertIn("text_mode_instructions", source)
        self.assertIn("СОХРАНИТЬ ИСХОДНЫЙ", source)
        self.assertIn("ПРОДАЮЩИЙ", source)
        self.assertIn("ОБУЧАЮЩИЙ", source)
        self.assertIn("КРАТКО СУТЬ", source)

    def test_custom_background_disables_ai_html_renderer(self):
        source = (PROJECT_ROOT / "handlers" / "carousel_flow.py").read_text(encoding="utf-8")

        custom_bg_branch = source[source.index("if custom_bg_bytes:"):source.index("else:", source.index("if custom_bg_bytes:"))]

        self.assertIn("render_layout_spec_html", custom_bg_branch)
        self.assertIn("allow_ai_html=False", custom_bg_branch)

    def test_cover_flow_explains_wide_format_as_cross_posting(self):
        source = (PROJECT_ROOT / "handlers" / "cover_flow.py").read_text(encoding="utf-8")

        self.assertIn("4:5 Instagram feed", source)
        self.assertIn("16:9", source)

    def test_cover_style_keyboard_is_compact_grid(self):
        from handlers.cover_flow import _style_keyboard

        keyboard = _style_keyboard()

        style_buttons = [btn for row in keyboard.inline_keyboard for btn in row if btn.callback_data.startswith("cover_style:")]
        self.assertEqual(len(style_buttons), 10)
        self.assertEqual(keyboard.inline_keyboard[0][0].text, "— Группа: плакатные —")
        self.assertEqual(keyboard.inline_keyboard[1][0].text, "Оранжевый постер")

    def test_insta_setup_copy_is_less_emoji_noisy(self):
        from handlers.common import INSTA_REWRITE_LABELS, INSTA_COLOR_LABELS

        self.assertEqual(INSTA_REWRITE_LABELS["concise"], "Короче")
        self.assertEqual(INSTA_COLOR_LABELS["auto"], "Авто")

    def test_slide_preview_avoids_markdown_parse_mode(self):
        source = (PROJECT_ROOT / "handlers" / "carousel_flow.py").read_text(encoding="utf-8")

        self.assertNotIn('preview_text, reply_markup=kb, parse_mode="Markdown"', source)
        self.assertNotIn("**Слайд", source)

    def test_fallback_message_is_not_hardcoded_as_chromium_problem(self):
        source = (PROJECT_ROOT / "handlers" / "carousel_flow.py").read_text(encoding="utf-8")

        self.assertNotIn("Для полноценных слайдов установите Chromium.", source)

    # ------------------------------------------------------------------
    # Experimental carousel pipeline (track: experimental-carousel-pipeline)
    # ------------------------------------------------------------------

    def test_experimental_renderer_module_exists(self):
        from pathlib import Path

        module_path = PROJECT_ROOT / "services" / "experimental_carousel_renderer.py"
        self.assertTrue(
            module_path.exists(),
            f"Expected {module_path} to exist on disk.",
        )

        import importlib

        module = importlib.import_module(
            "services.experimental_carousel_renderer"
        )
        for symbol in (
            "ExperimentalSlide",
            "build_experimental_slide_html",
            "map_layout_spec_to_experimental_slide",
            "render_experimental_carousel",
        ):
            self.assertTrue(
                hasattr(module, symbol),
                f"services.experimental_carousel_renderer must export {symbol}",
            )

    def test_insta_auto_result_has_no_test_render_buttons(self):
        """The three test-render style buttons must NOT appear in the
        ``run_insta_auto_pipeline`` result message. They live in the
        test-render mini-FSM now (track: test-render-entry-point).
        """

        source = (PROJECT_ROOT / "handlers" / "carousel_flow.py").read_text(encoding="utf-8")
        start = source.find("async def run_insta_auto_pipeline")
        end = source.find(
            '@router.callback_query(F.data.startswith("meta_prepare:")', start
        )
        self.assertNotEqual(start, -1)
        self.assertNotEqual(end, -1)
        block = source[start:end]
        for label in ("🧪 Dark+Teal", "🧪 Paper+Orange", "🧪 White+Coral"):
            self.assertNotIn(label, block)
        for callback in (
            "carousel_exp_render:{export_id}:dark_teal",
            "carousel_exp_render:{export_id}:paper_orange",
            "carousel_exp_render:{export_id}:white_coral",
        ):
            self.assertNotIn(callback, block)

    def test_experimental_render_callback_handler_exists(self):
        source = (PROJECT_ROOT / "handlers" / "carousel_flow.py").read_text(encoding="utf-8")
        self.assertIn("async def carousel_experimental_render", source)
        self.assertIn('F.data.startswith("carousel_exp_render:")', source)

    def test_experimental_renderer_persists_custom_background_data_url(self):
        source = (PROJECT_ROOT / "handlers" / "carousel_flow.py").read_text(encoding="utf-8")

        # Additive: a second update_export_metadata call must save the
        # custom-background data URL so the experimental renderer can
        # re-render with the same image.
        self.assertIn("custom_background_data_url", source)
        self.assertIn("update_export_metadata", source)
        # The data URL must come from the same image_bytes_to_data_url helper
        # already used elsewhere in the file.
        self.assertIn("image_bytes_to_data_url", source)

    def test_production_html_renderer_changes_are_preserved(self):
        """Guard against accidental revert of the readability fix in
        services/html_renderer.py and tests/test_html_renderer.py."""

        renderer_source = (PROJECT_ROOT / "services" / "html_renderer.py").read_text(
            encoding="utf-8"
        )
        tests_source = (PROJECT_ROOT / "tests" / "test_html_renderer.py").read_text(
            encoding="utf-8"
        )

        # Markers that came with the readability fix (uncommitted at handoff time).
        self.assertIn("_external_background_text_guard_css", renderer_source)
        self.assertIn("rgba(7, 10, 18, 0.56)", renderer_source)
        self.assertIn(
            "test_build_slide_html_forces_readable_ai_text_on_external_background",
            tests_source,
        )
        self.assertIn(
            "test_build_slide_html_softens_ai_root_background_for_external_bg",
            tests_source,
        )

    # ------------------------------------------------------------------
    # Experimental style-system track (exp-renderer-style-system)
    # ------------------------------------------------------------------

    def _insta_auto_block(self) -> str:
        """Return the source of run_insta_auto_pipeline.

        Tracked separately because the test-render entry point (track 3)
        moved the three style buttons out of this function.
        """
        source = (PROJECT_ROOT / "handlers" / "carousel_flow.py").read_text(encoding="utf-8")
        start = source.find("async def run_insta_auto_pipeline")
        self.assertNotEqual(start, -1, "run_insta_auto_pipeline not found")
        # The block ends at the next top-level @router.callback_query decorator.
        end = source.find('@router.callback_query(F.data.startswith("meta_prepare:")', start)
        if end == -1:
            # Fallback: stop at the first "@router.callback_query" after start.
            end = source.find("@router.callback_query", start)
        self.assertNotEqual(end, -1, "Could not find end of run_insta_auto_pipeline")
        return source[start:end]

    def test_three_experimental_style_buttons_removed_from_insta_auto(self):
        # Track 3 removed the three style buttons from run_insta_auto_pipeline
        # so the test-render entry point in the main menu is the single,
        # non-duplicated path to the experimental renderer.
        block = self._insta_auto_block()
        for label in ("Dark+Teal", "Paper+Orange", "White+Coral"):
            self.assertNotIn(label, block)
        for callback in (
            "carousel_exp_render:{export_id}:dark_teal",
            "carousel_exp_render:{export_id}:paper_orange",
            "carousel_exp_render:{export_id}:white_coral",
        ):
            self.assertNotIn(callback, block)

    def test_three_experimental_style_buttons_exist_in_test_render_section(self):
        # The three style buttons are now defined as a module-level
        # _TEST_RENDER_BUTTON_ROW, used by the test-render FSM.
        source = (PROJECT_ROOT / "handlers" / "carousel_flow.py").read_text(encoding="utf-8")
        self.assertIn("_TEST_RENDER_BUTTON_ROW", source)
        self.assertIn('"🧪 Dark+Teal"', source)
        self.assertIn('"🧪 Paper+Orange"', source)
        self.assertIn('"🧪 White+Coral"', source)
        # The callback prefix is test_render_style:<id>, not carousel_exp_render:.
        for style_id in ("dark_teal", "paper_orange", "white_coral"):
            self.assertIn(f"test_render_style:{style_id}", source)

    def test_experimental_renderer_exports_style_presets_dict(self):
        from services.experimental_carousel_renderer import STYLE_PRESETS

        self.assertEqual(set(STYLE_PRESETS.keys()), {"dark_teal", "paper_orange", "white_coral"})

    # ------------------------------------------------------------------
    # Test-render entry point track (test-render-entry-point)
    # ------------------------------------------------------------------

    def test_test_render_state_exists(self):
        from utils.states import TestRenderFlow

        self.assertEqual(
            TestRenderFlow.waiting_for_text.state,
            "TestRenderFlow:waiting_for_text",
        )

    def test_test_render_menu_button_is_admin_only(self):
        source = (PROJECT_ROOT / "handlers" / "common.py").read_text(encoding="utf-8")
        self.assertIn('"🧪 Тестовый рендер"', source)
        # The button must be added inside the cmd_start admin gate.
        admin_start = source.find("if message.from_user.id == ADMIN_ID:")
        self.assertNotEqual(admin_start, -1, "Admin gate not found in cmd_start")
        # Find the closing of this block: kb.append for /admin, then ].
        block = source[admin_start:admin_start + 600]
        self.assertIn("🧪 Тестовый рендер", block)

    def test_test_render_command_and_handlers_exist(self):
        source = (PROJECT_ROOT / "handlers" / "common.py").read_text(encoding="utf-8")
        self.assertIn('Command("test_render")', source)
        self.assertIn("F.text == \"🧪 Тестовый рендер\"", source)

    def test_test_render_callback_handler_uses_fsm_state(self):
        source = (PROJECT_ROOT / "handlers" / "carousel_flow.py").read_text(encoding="utf-8")
        # The style callback is gated by TestRenderFlow.waiting_for_style.
        self.assertIn("TestRenderFlow.waiting_for_style", source)
        self.assertIn('F.data.startswith("test_render_style:")', source)


if __name__ == "__main__":
    unittest.main()
