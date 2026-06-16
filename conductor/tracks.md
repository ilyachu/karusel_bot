# Tracks Registry

| ID | Title | Status | Created | Target |
|----|-------|--------|---------|--------|
| [experimental-carousel-pipeline](./tracks/experimental-carousel-pipeline/) | Experimental deterministic carousel renderer behind a separate test button | Approved (awaiting `Approve + go` and deploy) | 2026-06-16 | A/B visual stability |
| [exp-renderer-style-system](./tracks/exp-renderer-style-system/) | 4-axis style system + 3-style inline preview (Dark+Teal / Paper+Orange / White+Coral) for the experimental renderer | Approved (awaiting `Approve + go` and deploy) | 2026-06-16 | Real design variation to A/B against production |
| [test-render-entry-point](./tracks/test-render-entry-point/) | Separate 🧪 Тестовый рендер entry point in main menu with its own mini-FSM | Approved (awaiting `Approve + go` and deploy) | 2026-06-16 | Fast text-style iteration loop, no production render needed |
| [test-render-style-options](./tracks/test-render-style-options/) | Add rewrite_style picker (Как есть / Короче / Подробнее / Ярче) to the test-render mini-FSM | Approved (awaiting `Approve + go` and deploy) | 2026-06-16 | Half-control: vary textual content, not only visual style |
| [open-test-render-to-allowed-users](./tracks/open-test-render-to-allowed-users/) | Open 🆕 Карусель NEW to all allowed users; lift the button to the top of the main menu | Shipped | 2026-06-16 | Make the new pipeline usable by every whitelisted user |

## Conventions

- Track IDs are kebab-case slugs.
- Each track is a folder under `./tracks/<track_id>/`.
- Status moves: `Draft → Approved → Implementing → Verified → Shipped`.
- Status changes are recorded in `metadata.json`.
