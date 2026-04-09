## Phase 1: Production Foundation

### Goal

Turn the current Telegram carousel bot into a production-ready base for smarter
auto-layout rendering without introducing a new rendering stack yet.

### Scope

- Keep the existing bot flow intact.
- Clean repository/runtime hygiene.
- Make configuration deployment-safe.
- Replace the rigid single-layout renderer with a small layout engine that can
  adapt visuals to slide content.

### Non-goals

- Instagram publishing.
- New external infrastructure.
- Full HTML/JSX renderer migration.

### Execution Order

1. Lock current invariants with tests.
2. Clean repo/runtime concerns (`.env.example`, runtime artifacts, config).
3. Introduce a layout-aware rendering layer.
4. Rewire generation flow to use slide metadata in rendering.
5. Verify locally with tests.

### Expected Outcome

After Phase 1, the bot should still generate carousels through Telegram, but
the rendering layer should be easier to evolve into a true smart template
system in Phase 2.
