# Tracks Registry

| ID | Title | Status | Created | Target |
|----|-------|--------|---------|--------|
| [experimental-carousel-pipeline](./tracks/experimental-carousel-pipeline/) | Experimental deterministic carousel renderer behind a separate test button | Approved (awaiting `Approve + go` and deploy) | 2026-06-16 | A/B visual stability |
| [exp-renderer-style-system](./tracks/exp-renderer-style-system/) | 4-axis style system + 3-style inline preview (Dark+Teal / Paper+Orange / White+Coral) for the experimental renderer | Draft → awaiting approval | 2026-06-16 | Real design variation to A/B against production |

## Conventions

- Track IDs are kebab-case slugs.
- Each track is a folder under `./tracks/<track_id>/`.
- Status moves: `Draft → Approved → Implementing → Verified → Shipped`.
- Status changes are recorded in `metadata.json`.
