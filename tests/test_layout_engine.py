import unittest

from services.layout_engine import (
    DEFAULT_CTA_BODY,
    DEFAULT_CTA_TITLE,
    PRESET_VISUAL_PROFILES,
    VISUAL_MODE_LABELS,
    apply_theme_selection_policy,
    apply_theme_override,
    build_fallback_instagram_plan,
    build_instagram_layout_specs,
    enforce_default_cta_slide,
    parse_carousel_plan,
    resolve_preset_visual_profile,
    resolve_visual_mode,
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
                    "supporting_cards": [{"title": "вывод", "body": "сначала узкое применение"}],
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
        self.assertEqual(plan.slides[0].supporting_cards[0]["body"], "сначала узкое применение")
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

    def test_build_instagram_layout_specs_supports_editorial_visual_mode(self):
        plan = build_fallback_instagram_plan(
            [
                {"title": "Собрал себе систему знаний", "body": "Она помнит больше, чем я сам."},
                {"title": "490 тысяч", "body": "заметок, разговоров, чеков и писем в одной карте"},
                {"title": "Финал", "body": "Сохрани разбор и вернись позже."},
            ],
            theme_hint="memory_archive",
        )

        specs = build_instagram_layout_specs(plan, visual_mode="editorial")

        self.assertEqual(specs[0].visual_mode, "editorial")
        self.assertEqual(specs[0].variant, "editorial_cover")
        self.assertEqual(specs[1].variant, "editorial_stat")
        self.assertEqual(specs[-1].variant, "editorial_soft_cta")
        self.assertEqual(specs[0].section_number, "01")
        self.assertEqual(specs[1].watermark_number, "02")
        self.assertTrue(specs[1].footer_tags)
        self.assertEqual(specs[0].supporting_cards, [])
        self.assertEqual(specs[-1].progress_style, "line")

    def test_visual_mode_labels_include_product_presets(self):
        self.assertEqual(
            set(VISUAL_MODE_LABELS),
            {"auto", "classic", "editorial", "brief", "data"},
        )

    def test_preset_visual_profiles_use_new_layout_modes(self):
        self.assertEqual(set(PRESET_VISUAL_PROFILES), {"glitch", "lofi", "neon", "paper", "acid"})
        for preset_key in PRESET_VISUAL_PROFILES:
            with self.subTest(preset_key=preset_key):
                profile = resolve_preset_visual_profile(preset_key)
                self.assertIn(profile["theme"], {"memory_archive", "founder_brief", "growth_black", "research_mono"})
                self.assertIn(profile["visual_mode"], {"editorial", "brief", "data"})

    def test_unknown_preset_profile_falls_back_to_editorial(self):
        profile = resolve_preset_visual_profile("unknown")
        self.assertEqual(profile["theme"], "memory_archive")
        self.assertEqual(profile["visual_mode"], "editorial")

    def test_auto_visual_mode_prefers_data_for_numeric_api_posts(self):
        plan = build_fallback_instagram_plan(
            [
                {"title": "NVIDIA открыли 80 моделей", "body": "Подключение через OpenAI-compatible API и base URL."},
                {"title": "Цена ниже на 30%", "body": "Benchmark показывает рост скорости."},
                {"title": "Финал", "body": "Сохрани карусель."},
            ],
            theme_hint="research_mono",
        )

        decision = resolve_visual_mode(plan, "auto")
        specs = build_instagram_layout_specs(plan, visual_mode="auto")

        self.assertEqual(decision.resolved_mode, "data")
        self.assertEqual(specs[0].visual_mode, "data")
        self.assertTrue(any(spec.variant == "data_stat" for spec in specs))

    def test_auto_visual_mode_prefers_brief_for_founder_posts(self):
        plan = parse_carousel_plan(
            {
                "carousel": {"theme_hint": "founder_brief"},
                "slides": [
                    {"index": 1, "role": "hook", "title": "Product memo", "body": "Фаундер меняет pricing, GTM и roadmap запуска."},
                    {
                        "index": 2,
                        "role": "context",
                        "title": "Решение",
                        "body": "Сузить рынок и поднять ARPU.",
                        "supporting_cards": [{"title": "фокус", "body": "один ICP вместо трех"}],
                    },
                    {"index": 3, "role": "cta", "title": "Финал", "body": "Сохрани карусель."},
                ],
            }
        )

        decision = resolve_visual_mode(plan, "auto")
        specs = build_instagram_layout_specs(plan, visual_mode="auto")

        self.assertEqual(decision.resolved_mode, "brief")
        self.assertEqual(specs[0].visual_mode, "brief")
        self.assertEqual(specs[1].variant, "brief_decision")
        self.assertEqual(specs[1].supporting_cards[0]["body"], "один ICP вместо трех")

    def test_supporting_cards_reject_body_duplicates(self):
        plan = parse_carousel_plan(
            {
                "carousel": {"theme_hint": "founder_brief"},
                "slides": [
                    {"index": 1, "role": "hook", "title": "Обложка", "body": "Вводный слайд."},
                    {
                        "index": 2,
                        "role": "context",
                        "title": "Две версии под ваши задачи",
                        "body": "Обе версии уже работают в интерфейсе чата.",
                        "supporting_cards": [
                            {"title": "move", "body": "Обе версии уже работают"},
                            {"title": "выбор", "body": "Pro для глубокой аналитики"},
                        ],
                    },
                    {"index": 3, "role": "cta", "title": "Финал", "body": "Сохрани карусель."},
                ],
            }
        )

        specs = build_instagram_layout_specs(plan, visual_mode="brief")

        self.assertEqual(specs[1].supporting_cards, [{"title": "выбор", "body": "Pro для глубокой аналитики"}])

    def test_auto_visual_mode_defaults_to_editorial_for_narrative_news(self):
        plan = build_fallback_instagram_plan(
            [
                {"title": "Почему это важно", "body": "История показывает новый сценарий для команды."},
                {"title": "Контекст", "body": "Разбор без сильных числовых сигналов."},
                {"title": "Финал", "body": "Сохрани карусель."},
            ],
            theme_hint="memory_archive",
        )

        decision = resolve_visual_mode(plan, "auto")

        self.assertEqual(decision.resolved_mode, "editorial")

    def test_editorial_variant_does_not_treat_api_version_as_stat_slide(self):
        plan = build_fallback_instagram_plan(
            [
                {"title": "Обложка", "body": "Вводный слайд."},
                {
                    "title": "Меняете только base URL",
                    "body": "Достаточно указать https://integrate.api.nvidia.com/v1, вставить ключ и выбрать модель.",
                },
                {"title": "Финал", "body": "Сохрани карусель."},
            ],
            theme_hint="research_mono",
        )

        specs = build_instagram_layout_specs(plan, visual_mode="editorial")

        self.assertNotEqual(specs[1].variant, "editorial_stat")
        self.assertIn(specs[1].variant, {"editorial_story", "editorial_scenario"})

    def test_editorial_tags_prefer_meaningful_short_terms(self):
        plan = build_fallback_instagram_plan(
            [
                {"title": "Обложка", "body": "Вводный слайд."},
                {
                    "title": "Как подключить",
                    "body": "Регистрация через email, OTP, API Key и base URL для IDE.",
                },
                {"title": "Финал", "body": "Сохрани карусель."},
            ],
            theme_hint="research_mono",
        )

        specs = build_instagram_layout_specs(plan, visual_mode="editorial")

        self.assertIn("email", specs[1].footer_tags)
        self.assertIn("otp", specs[1].footer_tags)
        self.assertIn("api key", specs[1].footer_tags)

    def test_editorial_layout_does_not_set_foreign_brand_mark(self):
        plan = build_fallback_instagram_plan(
            [
                {"title": "DeepSeek V4 уже здесь", "body": "Открытая модель, которая догоняет лидеров."},
                {"title": "Финал", "body": "Сохрани карусель."},
            ],
            theme_hint="research_mono",
        )

        specs = build_instagram_layout_specs(plan, visual_mode="editorial")

        self.assertEqual(specs[0].brand_mark, "")

    def test_editorial_tags_extract_meaningful_terms_from_deepseek_slide(self):
        plan = build_fallback_instagram_plan(
            [
                {"title": "DeepSeek V4 уже здесь", "body": "Открытая модель, которая догоняет закрытые лидеры рынка. Разбираем, что изменилось в вычислениях."},
                {"title": "Финал", "body": "Сохрани карусель."},
            ],
            theme_hint="research_mono",
        )

        specs = build_instagram_layout_specs(plan, visual_mode="editorial")

        self.assertIn("deepseek", specs[0].footer_tags)
        self.assertIn("вычислениях", specs[0].footer_tags)

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

    def test_editorial_cta_is_softer_than_classic_default(self):
        plan = build_fallback_instagram_plan(
            [
                {"title": "Слайд 1", "body": "Текст 1"},
                {"title": "Слайд 2", "body": "Текст 2"},
                {"title": "Слайд 3", "body": "Текст 3"},
            ],
            theme_hint="founder_brief",
        )
        updated = enforce_default_cta_slide(plan, visual_mode="editorial")

        self.assertEqual(updated.slides[-1].role, "cta")
        self.assertNotEqual(updated.slides[-1].title, DEFAULT_CTA_TITLE)
        self.assertIn("Сохрани", updated.slides[-1].title)


if __name__ == "__main__":
    unittest.main()
