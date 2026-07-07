"""Tests for carousel copy length guidelines."""

from __future__ import annotations

import unittest

from services.carousel_content_guidelines import (
    LIMITS,
    clamp_carousel_plan,
    clamp_carousel_plan_dict,
    clamp_slide_dict,
    content_limits_prompt_block,
)
from services.layout_engine import CarouselPlan, SlidePlanEntry, parse_carousel_plan


class CarouselContentGuidelinesTests(unittest.TestCase):
    def test_prompt_block_mentions_limits(self):
        block = content_limits_prompt_block()
        self.assertIn(str(LIMITS["hook_title"]), block)
        self.assertIn("stat_panel", block)

    def test_clamp_slide_dict_truncates_hook_title(self):
        long_title = "А" * 140
        clamped = clamp_slide_dict(
            {"role": "hook", "title": long_title, "body": "короткий подзаголовок"}
        )
        self.assertLessEqual(len(clamped["title"]), LIMITS["hook_title"])

    def test_clamp_slide_dict_splits_list_density(self):
        body = "Пункт один\nПункт два\nПункт три\nПункт четыре"
        clamped = clamp_slide_dict(
            {
                "role": "point",
                "archetype": "checklist_stack",
                "title": "Шаги",
                "body": body,
                "density": "high",
            }
        )
        self.assertEqual(clamped["density"], "high")
        self.assertIn("\n", clamped["body"])

    def test_clamp_carousel_plan_dict_preserves_structure(self):
        raw = {
            "carousel": {"goal": "instagram_carousel", "theme_hint": "business_dark"},
            "slides": [
                {
                    "index": 1,
                    "role": "hook",
                    "title": "X" * 200,
                    "body": "Y" * 300,
                    "density": "low",
                }
            ],
        }
        clamped = clamp_carousel_plan_dict(raw)
        self.assertLessEqual(len(clamped["slides"][0]["title"]), LIMITS["hook_title"])
        self.assertLessEqual(len(clamped["slides"][0]["body"]), LIMITS["hook_body"])

    def test_clamp_carousel_plan_on_parsed_plan(self):
        plan = parse_carousel_plan(
            {
                "carousel": {"theme_hint": "business_dark"},
                "slides": [
                    {
                        "index": 1,
                        "role": "cta",
                        "title": "C" * 120,
                        "body": "D" * 400,
                        "density": "low",
                    }
                ],
            }
        )
        clamped = clamp_carousel_plan(plan)
        self.assertIsInstance(clamped, CarouselPlan)
        self.assertLessEqual(len(clamped.slides[0].title), LIMITS["cta_title"])
        self.assertLessEqual(len(clamped.slides[0].body), LIMITS["cta_body"])


if __name__ == "__main__":
    unittest.main()