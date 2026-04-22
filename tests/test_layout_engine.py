import unittest

from services.layout_engine import (
    DEFAULT_CTA_BODY,
    DEFAULT_CTA_TITLE,
    apply_theme_selection_policy,
    apply_theme_override,
    build_fallback_instagram_plan,
    build_instagram_layout_specs,
    enforce_default_cta_slide,
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
        raw = {
            "carousel": {"theme_hint": "business_dark"},
            "slides": [
                {"index": 1, "role": "hook", "title": "Хук", "body": "Первый слайд", "density": "low"},
                {"index": 2, "role": "context", "title": "Контекст", "body": "Второй слайд, более длинный контекст с деталями.", "density": "medium"},
                {"index": 3, "role": "point", "title": "Цитата", "body": "Короткий сильный вывод.", "density": "low"},
                {"index": 4, "role": "cta", "title": "CTA", "body": "Финальный слайд", "density": "low"},
            ],
        }
        plan = parse_carousel_plan(raw)
        specs = build_instagram_layout_specs(plan)

        self.assertEqual(specs[0].variant, "cover")
        self.assertEqual(specs[1].variant, "framework_grid")
        self.assertEqual(specs[2].variant, "quote")
        self.assertEqual(specs[-1].variant, "closing")
        self.assertTrue(all(spec.theme == "business_dark" for spec in specs))

    def test_badges_are_added_but_support_cards_stay_for_real_checklists_only(self):
        raw = {
            "carousel": {"theme_hint": "memory_archive"},
            "slides": [
                {"index": 1, "role": "hook", "title": "Поговорим про память", "body": "Контекстное окно растет.", "density": "low"},
                {"index": 2, "role": "context", "title": "Почему тема болит", "body": "Проекты длиннее, цепочки сложнее, а договоренности уже не помещаются в один чат.", "density": "high"},
                {"index": 3, "role": "cta", "title": "Что делать", "body": "Сохрани пост и вернись к нему позже.", "density": "low"},
            ],
        }
        plan = parse_carousel_plan(raw)
        specs = build_instagram_layout_specs(plan)

        self.assertEqual(specs[1].variant, "framework_grid")
        self.assertEqual(specs[1].supporting_cards, [])
        self.assertEqual(specs[0].badge_text, "Главное")

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

    def test_default_cta_slide_always_replaces_last_slide(self):
        plan = build_fallback_instagram_plan(
            [
                {"title": "Слайд 1", "body": "Текст 1"},
                {"title": "Слайд 2", "body": "Текст 2"},
                {"title": "Слайд 3", "body": "Текст 3"},
            ],
            theme_hint="research_mono",
        )
        updated = enforce_default_cta_slide(plan)

        self.assertEqual(updated.slides[-1].role, "cta")
        self.assertEqual(updated.slides[-1].title, DEFAULT_CTA_TITLE)
        self.assertEqual(updated.slides[-1].body, DEFAULT_CTA_BODY)


if __name__ == "__main__":
    unittest.main()
