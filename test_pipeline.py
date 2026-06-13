#!/usr/bin/env python3
"""Test the full carousel pipeline programmatically."""

import asyncio
import json
import logging
import sys
import os

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

TEST_TEXT = """⚡️ Xiaomi выпустили MiMo Code — своего coding-агента

Вслед за Kimi (https://t.me/ai_for_devs/435) ещё одна китайская компания обзавелась своим агентом. 

Основной упор в релизной статье (https://mimo.xiaomi.com/zh/blog/mimo-code-long-horizon) китайцы делают на Max Mode: на каждом шаге агент генерирует 5 параллельных планов действий, а модель-судья выбирает лучший, остальные отбрасываются. 

По SWE-Bench Pro прирост у Mimo-V2.5-Pro до 20% за 4-5× больше токенов.

MIT-лицензия, open source (https://github.com/XiaomiMiMo/MiMo-Code), построен на OpenCode."""


async def test_carousel_plan():
    """Test 1: Generate carousel plan."""
    print("\n" + "="*60)
    print("TEST 1: generate_instagram_carousel_plan")
    print("="*60)
    
    from services.gemini_client import generate_instagram_carousel_plan
    
    word_count = len(TEST_TEXT.split())
    target_slides = max(4, min(7, word_count // 15 + 2))
    print(f"Word count: {word_count}, Target slides: {target_slides}")
    
    result = await generate_instagram_carousel_plan(TEST_TEXT, target_slides, "concise")
    
    if not result:
        print("❌ FAILED: Empty result")
        return None
    
    print(f"✅ Got result with keys: {list(result.keys())}")
    
    carousel = result.get("carousel", {})
    slides = result.get("slides", [])
    
    print(f"   carousel.layout_style: {carousel.get('layout_style')}")
    print(f"   carousel.theme_hint: {carousel.get('theme_hint')}")
    print(f"   carousel.tone: {carousel.get('tone')}")
    print(f"   slides count: {len(slides)}")
    
    for i, slide in enumerate(slides):
        print(f"   Slide {i+1}: role={slide.get('role')}, title={slide.get('title', '')[:50]}")
    
    return result


async def test_caption():
    """Test 2: Generate Instagram caption."""
    print("\n" + "="*60)
    print("TEST 2: generate_instagram_caption")
    print("="*60)
    
    from services.gemini_client import generate_instagram_caption
    
    slides_content = [
        {"title": "MiMo Code", "body": "Xiaomi выпустили coding-агента"},
        {"title": "Max Mode", "body": "5 параллельных планов, модель-судья"},
        {"title": "SWE-Bench Pro", "body": "+20% за 4-5× токенов"},
        {"title": "Open Source", "body": "MIT-лицензия, построен на OpenCode"},
    ]
    
    result = await generate_instagram_caption(TEST_TEXT, slides_content)
    
    if not result:
        print("❌ FAILED: Empty caption")
        return None
    
    print(f"✅ Caption length: {len(result)} chars")
    print(f"   First 200 chars: {result[:200]}...")
    
    return result


async def test_layout_specs():
    """Test 3: Build layout specs for all styles."""
    print("\n" + "="*60)
    print("TEST 3: build_instagram_layout_specs (all styles)")
    print("="*60)
    
    from services.layout_engine import (
        build_instagram_layout_specs,
        build_fallback_instagram_plan,
        CarouselPlan,
        SlidePlanEntry,
    )
    
    slides = [
        SlidePlanEntry(index=1, role="hook", title="MiMo Code", body="Xiaomi выпустили coding-агента", emphasis=[], density="medium", theme_hint="business_dark", supporting_cards=[]),
        SlidePlanEntry(index=2, role="context", title="Max Mode", body="5 параллельных планов, модель-судья выбирает лучший", emphasis=[], density="medium", theme_hint="business_dark", supporting_cards=[]),
        SlidePlanEntry(index=3, role="point", title="SWE-Bench Pro", body="+20% за 4-5× токенов", emphasis=[], density="medium", theme_hint="business_dark", supporting_cards=[]),
        SlidePlanEntry(index=4, role="cta", title="Open Source", body="MIT-лицензия, построен на OpenCode", emphasis=[], density="low", theme_hint="business_dark", supporting_cards=[]),
    ]
    
    plan = CarouselPlan(
        goal="instagram_carousel",
        audience="developers",
        tone="clear_confident",
        theme_hint="business_dark",
        cta="save_and_follow",
        layout_style="magazine",
        slides=slides,
    )
    
    results = {}
    for style in ["magazine", "terminal", "poster", "carddeck"]:
        specs = build_instagram_layout_specs(plan, visual_mode="auto", layout_style=style)
        results[style] = len(specs)
        print(f"   {style}: {len(specs)} specs, first title='{specs[0].title}'")
    
    print(f"✅ All styles generated specs: {results}")
    return results


async def test_html_render():
    """Test 4: Render HTML for each layout style."""
    print("\n" + "="*60)
    print("TEST 4: Render HTML for each layout style")
    print("="*60)
    
    from services.layout_engine import (
        build_instagram_layout_specs,
        CarouselPlan,
        SlidePlanEntry,
    )
    from services.html_renderer import render_layout_spec_html
    
    slides = [
        SlidePlanEntry(index=1, role="hook", title="MiMo Code", body="Xiaomi выпустили coding-агента", emphasis=[], density="medium", theme_hint="business_dark", supporting_cards=[]),
        SlidePlanEntry(index=2, role="context", title="Max Mode", body="5 параллельных планов", emphasis=[], density="medium", theme_hint="business_dark", supporting_cards=[]),
    ]
    
    plan = CarouselPlan(
        goal="instagram_carousel",
        audience="developers",
        tone="clear_confident",
        theme_hint="business_dark",
        cta="save_and_follow",
        layout_style="magazine",
        slides=slides,
    )
    
    results = {}
    for style in ["magazine", "terminal", "poster", "carddeck"]:
        specs = build_instagram_layout_specs(plan, visual_mode="auto", layout_style=style)
        try:
            png = render_layout_spec_html(specs[0], "chu ai")
            results[style] = len(png)
            print(f"   {style}: ✅ PNG size={len(png)} bytes")
        except Exception as e:
            results[style] = f"ERROR: {e}"
            print(f"   {style}: ❌ {e}")
    
    return results


async def test_cover_plan():
    """Test 5: Generate cover plan for all styles."""
    print("\n" + "="*60)
    print("TEST 5: generate_cover_plan (all styles)")
    print("="*60)
    
    from services.gemini_client import generate_cover_plan
    
    results = {}
    for style in ["orange_poster", "blue_type", "retro_polaroid", "quiet_editorial"]:
        try:
            result = await generate_cover_plan(TEST_TEXT, style, "post")
            results[style] = {
                "headline": result.get("headline", ""),
                "subtitle": result.get("subtitle", ""),
                "cta_text": result.get("cta_text", ""),
            }
            print(f"   {style}: headline='{result.get('headline', '')}'")
        except Exception as e:
            results[style] = f"ERROR: {e}"
            print(f"   {style}: ❌ {e}")
    
    return results


async def test_cover_render():
    """Test 6: Render covers for all styles."""
    print("\n" + "="*60)
    print("TEST 6: Render covers for all styles")
    print("="*60)
    
    from services.cover_renderer import CoverPlan, render_cover_html, COVER_STYLES
    
    results = {}
    for style in list(COVER_STYLES.keys())[:4]:
        try:
            plan = CoverPlan(
                headline="MiMo Code",
                subtitle="Xiaomi выпустили coding-агента",
                eyebrow_left="РАЗБОР · № 01",
                eyebrow_right="POSTER · TODAY",
                footer_left="ДЛЯ РАЗРАБОТЧИКОВ",
                symbol="arrow",
                style=style,
                format_key="post",
            )
            png = render_cover_html(plan)
            results[style] = len(png)
            print(f"   {style}: ✅ PNG size={len(png)} bytes")
        except Exception as e:
            results[style] = f"ERROR: {e}"
            print(f"   {style}: ❌ {e}")
    
    return results


async def main():
    print("🧪 FULL PIPELINE TEST")
    print(f"Text: {TEST_TEXT[:80]}...")
    
    results = {}
    
    # Test 1: Carousel plan
    results["carousel_plan"] = await test_carousel_plan()
    
    # Test 2: Caption
    results["caption"] = await test_caption()
    
    # Test 3: Layout specs
    results["layout_specs"] = await test_layout_specs()
    
    # Test 4: HTML render
    results["html_render"] = await test_html_render()
    
    # Test 5: Cover plan
    results["cover_plan"] = await test_cover_plan()
    
    # Test 6: Cover render
    results["cover_render"] = await test_cover_render()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_ok = True
    for test_name, result in results.items():
        if result is None:
            print(f"   {test_name}: ❌ FAILED (None)")
            all_ok = False
        elif isinstance(result, dict):
            errors = {k: v for k, v in result.items() if isinstance(v, str) and "ERROR" in v}
            if errors:
                print(f"   {test_name}: ⚠️ PARTIAL - {len(errors)} errors: {errors}")
                all_ok = False
            else:
                print(f"   {test_name}: ✅ OK ({len(result)} items)")
        elif isinstance(result, str):
            print(f"   {test_name}: ✅ OK ({len(result)} chars)")
        else:
            print(f"   {test_name}: ✅ OK")
    
    if all_ok:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️ SOME TESTS FAILED - check logs above")
    
    return all_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
