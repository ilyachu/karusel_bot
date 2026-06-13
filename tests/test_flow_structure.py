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

    def test_create_carousel_uses_insta_auto_setup(self):
        source = (PROJECT_ROOT / "handlers" / "common.py").read_text(encoding="utf-8")

        self.assertIn("async def start_insta_creation_setup", source)
        self.assertIn("async def cmd_create_carousel", source)
        self.assertIn("start_insta_creation_setup(", source)

    def test_insta_auto_style_packs_are_product_facing(self):
        from handlers.common import INSTA_CARD_FORMAT_LABELS, INSTA_VISUAL_PRESETS

        self.assertEqual(INSTA_VISUAL_PRESETS["calm"]["label"], "Спокойный")
        self.assertIn("понятный шрифт", INSTA_VISUAL_PRESETS["calm"]["description"])
        self.assertEqual(INSTA_VISUAL_PRESETS["contrast"]["label"], "Контрастный")
        self.assertEqual(INSTA_VISUAL_PRESETS["contrast"]["theme"], "growth_black")
        self.assertEqual(INSTA_VISUAL_PRESETS["contrast"]["visual_mode"], "editorial")
        self.assertEqual(INSTA_CARD_FORMAT_LABELS["classic"], "Читабельно")

    def test_cover_flow_explains_wide_format_as_cross_posting(self):
        source = (PROJECT_ROOT / "handlers" / "cover_flow.py").read_text(encoding="utf-8")

        self.assertIn("4:5 Instagram feed", source)
        self.assertIn("16:9", source)

    def test_cover_style_keyboard_is_compact_grid(self):
        from handlers.cover_flow import _style_keyboard

        keyboard = _style_keyboard()

        style_buttons = [btn for row in keyboard.inline_keyboard for btn in row if btn.callback_data.startswith("cover_style:")]
        self.assertEqual(len(style_buttons), 10)
        self.assertEqual(keyboard.inline_keyboard[0][0].text, "— Плакаты —")
        self.assertEqual(keyboard.inline_keyboard[1][0].text, "Оранжевый постер")

    def test_slide_preview_avoids_markdown_parse_mode(self):
        source = (PROJECT_ROOT / "handlers" / "carousel_flow.py").read_text(encoding="utf-8")

        self.assertNotIn('preview_text, reply_markup=kb, parse_mode="Markdown"', source)
        self.assertNotIn("**Слайд", source)


if __name__ == "__main__":
    unittest.main()
