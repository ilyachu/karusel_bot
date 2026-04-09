## Phase 2: Instagram-Ready Output

### What is implemented now

- `🚀 Insta Auto` mode in Telegram.
- Automatic slide count selection for Instagram-style carousels.
- Automatic caption generation.
- Export package with `slide_XX.png`, `caption.txt`, and `metadata.json`.

### Why auto-publishing is not wired yet

For stable production publishing to Instagram, the bot needs the official Meta
Business publishing path. That requires:

- an Instagram Business or Creator account
- a Meta app
- publishing permissions
- long-lived access tokens
- publicly accessible URLs for generated slide images

### Recommended next step

Add a dedicated publish layer:

1. Export slides to object storage with public URLs.
2. Create a Meta publishing service on top of the export package.
3. Add a publish approval button in Telegram after preview/export.
