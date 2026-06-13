# User Business Path and Value Map

Date: 2026-04-25
Product: `@karusel_chu_bot`

## Product Promise

User brings raw thought, voice, or repost. Bot returns an Instagram-ready carousel with preview, caption, export package, and publish actions.

Core value:
- reduce time from idea to publishable post;
- make output visually stronger than a plain Telegram text split;
- reduce decisions before first result;
- keep enough control for style, caption, and publishing.

## Primary User

Creator / founder / marketer who already has content material but does not want to manually:
- rewrite text into slide logic;
- design every slide;
- create caption;
- export image files;
- publish separately to Instagram and Threads.

## Business Path

### 1. Entry

User opens bot and sees:
- `Создать карусель`
- `🚀 Insta Auto`
- `🖼 Обложка`
- logo settings

Desired meaning:
- `Создать карусель`: main business path.
- `Insta Auto`: fast expert/default path, now technically same pipeline.
- `Обложка`: standalone design asset path.

Value:
- user understands the bot can either create a full carousel or only a cover.

Risk:
- two carousel entry labels can feel redundant.

Recommended next decision:
- keep both temporarily while measuring behavior;
- later rename `🚀 Insta Auto` to `Авто-режим` or remove if `Создать карусель` fully absorbs it.

### 2. Setup

User chooses or keeps defaults:
- text rewrite style;
- design/color style;
- typography/grid;
- 4:5 Instagram size;
- optional custom background.

Value:
- user sees controllable product language instead of internal render names.
- default `auto` keeps the fast path.

Current style intent:
- `Спокойный`: calm colors, readable type, clean analysis.
- `Контрастный`: cover-like, darker, larger, more noticeable.
- `Мемо`: strict product/founder note.
- `Факты`: numbers, comparisons, news, tools.

Risk:
- too many controls can still slow first-time users.

Recommended next decision:
- collapse default screen to one visible row: `Авто / Спокойный / Контраст / Мемо / Факты`;
- move text rewrite and typography to `Настроить подробнее`.

### 3. Input

User sends:
- raw text;
- voice;
- forwarded post.

Pipeline:
- validate length;
- transcribe if voice;
- generate carousel plan;
- choose slide count;
- choose/lock visual style;
- generate caption and Threads summary;
- render slides;
- save export package.

Value:
- raw material becomes a publish-ready artifact.

Risk:
- if generation takes too long, user needs progress messages that explain what is happening.

Recommended next decision:
- add 3 progress statuses:
  - `Разбираю смысл`
  - `Собираю структуру слайдов`
  - `Рендерю карточки`

### 4. Preview

User receives:
- media group with slides;
- summary: slide count, text style, visual style, render mode, export id;
- caption preview;
- publish buttons.

Value:
- user can inspect final artifact before publishing.

Risk:
- current result summary exposes technical fields like `render_mode` and `export_id`.

Recommended next decision:
- user-facing summary should show:
  - `Стиль`
  - `Слайдов`
  - `Подпись`
  - `Готово к публикации`
- move `render_mode` and `export_id` to admin/debug only.

### 5. Action

User can:
- publish to Instagram;
- publish to Threads.

Admin can:
- prepare advanced Meta plan.

Value:
- closes the loop from content creation to publishing.

Risk:
- user also needs post-generation controls:
  - regenerate text;
  - change visual style;
  - edit caption;
  - create separate 16:9 cover.

Recommended next decision:
- add second action row after preview:
  - `🔄 Перегенерировать текст`
  - `🎨 Сменить стиль`
  - `✍️ Изменить caption`
  - `🖼 Сделать обложку`

## Standalone Cover Path

User sends text, chooses style, background, and format.

Formats:
- 4:5 Instagram feed default.
- 16:9 wide cover for Telegram/site/YouTube/landscape cross-posting.
- 9:16 story/reels.

Value:
- user can create one strong visual asset without full carousel.

Risk:
- uploaded background quality depends on contrast/crop.

Recommended next decision:
- add auto contrast/focal crop improvements;
- for Instagram publishing of wide images, add API-safe JPEG output.

## Value Ladder

### Basic Value

Split text into slides and make PNGs.

### Product Value

Produce a coherent Instagram post:
- hook;
- slide structure;
- visual style;
- caption;
- export;
- publish.

### Business Value

Save time and increase output consistency:
- less manual editing;
- fewer design decisions;
- repeatable brand styles;
- faster publishing cadence.

### Premium Value Later

Possible future monetizable layers:
- saved brand kits;
- recurring creator styles;
- team/workspace exports;
- content calendar;
- analytics of published posts;
- one-click repurpose into Threads, Reels cover, story, Telegram post.

## Current Best Next Product Move

Do not add more visual options yet.

Next best iteration:
1. Simplify setup screen to one primary style selector.
2. Hide technical fields after generation.
3. Add post-preview edit actions.
4. Render 4 real sample posts across `Спокойный`, `Контрастный`, `Мемо`, `Факты`.
5. Use those samples to decide whether renderer palettes/layouts need another visual pass.

