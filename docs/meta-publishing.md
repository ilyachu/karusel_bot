## Meta Publishing Scaffold

This project is prepared for the **Instagram API with Instagram Login** path,
but the actual publish flow is still scaffold-only.

### Official baseline

Current official direction for a new build:
- use a **Meta Business app**
- connect it to a **verified business**
- publish to an **Instagram professional account**
- for testing, use a **public** professional account

Official references:
- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/create-a-meta-app-with-instagram
- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing

### Required permissions

- `instagram_business_basic`
- `instagram_business_content_publish`

### Carousel publishing shape

1. Create one media container per slide with:
   - `POST /{ig_user_id}/media`
   - `image_url=<public slide URL>`
   - `is_carousel_item=true`
2. Create the parent carousel container with:
   - `POST /{ig_user_id}/media`
   - `media_type=CAROUSEL`
   - `children=<comma-separated child container ids>`
   - `caption=<final caption>`
3. Publish with:
   - `POST /{ig_user_id}/media_publish`
   - `creation_id=<carousel container id>`
4. Poll container readiness with:
   - `GET /{creation_id}?fields=status_code`
   - once per minute for up to 5 minutes

### Project contract

The export package is the publish boundary:
- slides are already rendered
- caption is already written
- metadata already contains plan/layout/theme context

The Meta layer should consume that package, not rebuild content from Telegram
history.

### What is scaffolded in code

`services/meta_publish.py` contains:
- app config model
- Instagram credentials model
- export metadata loader
- request builders for:
  - child media containers
  - parent carousel container
  - publish call
  - status polling

### What is still missing

- real OAuth/login flow
- persistent encrypted storage for per-tenant Instagram tokens
- public hosting for slide PNGs
- actual HTTP execution + retry logic
- Telegram approval button that triggers publishing
