# Product Definition — karusel_bot

## What

A Telegram bot that turns a single block of Russian text into a ready-to-post Instagram / Threads carousel. The bot plans the carousel structure, picks a visual style, generates a hero cover, and exports an Instagram-ready package.

## Who

- Russian-speaking creators, educators, and indie founders who publish carousel content on Instagram and Threads.
- They want a fast, opinionated tool that turns long-form Russian text into visual content with minimal manual work.

## Why

- Manual carousel design is slow and visually inconsistent.
- AI-generated HTML for carousels is unstable: contrast, backgrounds, and typography drift between generations.
- Creators need a deterministic, readable baseline they can trust and iterate on.

## Core Capabilities

1. Receive a block of Russian text via Telegram.
2. Plan a carousel (slide count, roles, hooks, CTAs, body) using a deterministic + LLM-assisted planning pipeline.
3. Render slides as 1080x1350 PNGs.
4. Export a complete Instagram package (slides, caption, metadata).
5. (Experimental) Re-render the same planned carousel through a deterministic template pipeline to A/B visual stability.

## Non-Goals

- Multi-language support (Russian is the primary language).
- Web UI (Telegram is the only surface).
- Direct publishing without an admin's deliberate action.
- Auto-scheduling of posts.
