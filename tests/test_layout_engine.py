import unittest

from services.layout_engine import (
    build_fallback_instagram_plan,
    build_instagram_layout_specs,
    parse_carousel_plan,
)


class LayoutEngineTests(unittest.TestCase):
    def test_parse_carousel_plan_preserves_roles_and_theme(self):
        raw = {
            "carousel": {
                "goal": "instagram_carousel",
                "audience": "founders",
                "tone": "clear_confident",
                "theme_hint": "business_dark",
                "cta": "save_and_follow",
            },
            "slides": [
                {
                    "index": 1,
                    "role": "hook",
                    "title": "5 задач AI-оператора",
                    "body": "Короткий вводный текст.",
                    "emphasis": ["5 задач", "AI-оператора"],
                    "density": "medium",
                    "theme_hint": "business_dark",
                },
                {
                    "index": 2,
                    "role": "cta",
                    "title": "Сохрани пост",
                    "body": "Вернись к нему позже.",
                    "emphasis": ["Сохрани"],
                    "density": "low",
                    "theme_hint": "business_dark",
                },
            ],
        }

        plan = parse_carousel_plan(raw)
        self.assertEqual(plan.theme_hint, "business_dark")
        self.assertEqual(plan.slides[0].role, "hook")
        self.assertEqual(plan.slides[1].role, "cta")

    def test_build_instagram_layout_specs_maps_roles_to_variants(self):
        plan = build_fallback_instagram_plan(
            [
                {"title": "Хук", "body": "Первый слайд"},
                {"title": "Контекст", "body": "Второй слайд"},
                {"title": "CTA", "body": "Финальный слайд"},
            ]
        )
        specs = build_instagram_layout_specs(plan)

        self.assertEqual(specs[0].variant, "cover")
        self.assertEqual(specs[-1].variant, "closing")
        self.assertTrue(all(spec.theme == "business_dark" for spec in specs))

    def test_supporting_cards_stay_within_zero_to_three_items(self):
        plan = build_fallback_instagram_plan(
            [
                {"title": "Поговорим про память", "body": "Контекстное окно растет. Задачи растут быстрее."},
                {"title": "Почему тема болит", "body": "Проекты длиннее, цепочки сложнее, а договоренности уже не помещаются в один чат."},
                {"title": "Что делать", "body": "Сохрани пост и вернись к нему позже."},
            ],
            theme_hint="memory_archive",
        )
        specs = build_instagram_layout_specs(plan)

        self.assertTrue(all(0 <= len(spec.supporting_cards) <= 3 for spec in specs))
        self.assertGreaterEqual(len(specs[0].supporting_cards), 1)
        self.assertGreaterEqual(len(specs[1].supporting_cards), 1)
        self.assertEqual(len(specs[-1].supporting_cards), 1)


if __name__ == "__main__":
    unittest.main()
