import unittest

from services.layout_engine import (
    apply_theme_selection_policy,
    apply_theme_override,
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

        self.assertTrue(all(0 <= len(spec.supporting_cards) <= 2 for spec in specs))
        self.assertTrue(all(card["label"] == "" for spec in specs for card in spec.supporting_cards))

    def test_theme_selection_policy_prefers_memory_archive_for_memory_posts(self):
        plan = build_fallback_instagram_plan(
            [{"title": "Поговорим про память", "body": "Память, контекст и MemPalace для AI агентов."}],
            theme_hint="business_dark",
        )
        selected, decision = apply_theme_selection_policy(plan, "Память, контекст, Telegram и MemPalace для AI агентов")
        self.assertEqual(selected.theme_hint, "memory_archive")
        self.assertEqual(decision.selected_theme, "memory_archive")

    def test_theme_selection_policy_prefers_growth_black_for_growth_posts(self):
        plan = build_fallback_instagram_plan(
            [{"title": "Рост выручки", "body": "CAC, ROMI, конверсии и трафик."}],
            theme_hint="business_dark",
        )
        selected, _ = apply_theme_selection_policy(plan, "Разбор роста, CAC, ROMI, performance marketing и выручки")
        self.assertEqual(selected.theme_hint, "growth_black")

    def test_theme_selection_policy_prefers_research_mono_for_framework_posts(self):
        plan = build_fallback_instagram_plan(
            [{"title": "Фреймворк памяти", "body": "Research, architecture, protocol, benchmark."}],
            theme_hint="business_dark",
        )
        selected, _ = apply_theme_selection_policy(plan, "Research on memory architecture, benchmark protocol and framework")
        self.assertEqual(selected.theme_hint, "research_mono")

    def test_theme_selection_policy_prefers_founder_brief_for_founder_posts(self):
        plan = build_fallback_instagram_plan(
            [{"title": "Product memo", "body": "Фаундер, стратегия, запуск и roadmap."}],
            theme_hint="business_dark",
        )
        selected, _ = apply_theme_selection_policy(plan, "Фаундер, продукт, стратегия, roadmap и запуск")
        self.assertEqual(selected.theme_hint, "founder_brief")

    def test_theme_override_forces_selected_theme(self):
        plan = build_fallback_instagram_plan(
            [{"title": "Growth memo", "body": "CAC, ROMI, трафик и performance marketing."}],
            theme_hint="business_dark",
        )
        selected, decision = apply_theme_override(plan, "research_mono")
        self.assertEqual(selected.theme_hint, "research_mono")
        self.assertEqual(decision.selected_theme, "research_mono")
        self.assertIn("forced", decision.reason)


if __name__ == "__main__":
    unittest.main()
