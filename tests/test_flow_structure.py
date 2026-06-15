import ast
from pathlib import Path
import unittest


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


if __name__ == "__main__":
    unittest.main()
