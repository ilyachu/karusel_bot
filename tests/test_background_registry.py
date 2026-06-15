import unittest

from services.background_registry import (
    BACKGROUND_PRESETS,
    BACKGROUND_PRESET_MAP,
    pick_background_preset,
)


class BackgroundRegistryTests(unittest.TestCase):
    def test_background_presets_are_registered(self):
        self.assertEqual(len(BACKGROUND_PRESETS), 11)
        self.assertIn("soft_red_spray", BACKGROUND_PRESET_MAP)
        self.assertIn("blue_crumple", BACKGROUND_PRESET_MAP)

    def test_pick_background_preset_prefers_compatible_style_and_theme(self):
        preset = pick_background_preset(
            layout_style="magazine",
            theme_hint="memory_archive",
            slide_role="context",
            archetype="split_story",
        )

        self.assertIsNotNone(preset)
        self.assertIn("magazine", preset.fit_styles)
        self.assertIn("memory_archive", preset.fit_themes)

    def test_pick_background_preset_uses_bold_assets_for_poster_hooks(self):
        preset = pick_background_preset(
            layout_style="poster",
            theme_hint="creator_bold",
            slide_role="hook",
            archetype="hero_center",
        )

        self.assertIsNotNone(preset)
        self.assertIn(preset.preset_id, {"acid_swirl", "pink_foil", "lime_flower", "soft_red_spray"})


if __name__ == "__main__":
    unittest.main()
