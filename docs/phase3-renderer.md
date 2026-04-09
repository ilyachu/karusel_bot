## Phase 3: Rich Insta Auto Renderer

### Goal

Upgrade `🚀 Insta Auto` from the transitional Pillow layout engine to a richer
HTML/CSS renderer without breaking the existing manual flows.

### Approach

- Keep `carousel plan -> layout specs -> render` as the core contract.
- Add a dedicated HTML renderer for `LayoutSpec`.
- Render via Playwright/Chromium for better composition fidelity.
- Keep the Pillow renderer as a fallback path.

### Scope

- New renderer only for `Insta Auto`.
- Existing manual and fast modes continue using the current renderer.
- Update deployment/runtime instructions for Playwright browser binaries.

### Non-goals

- Meta publishing API integration.
- Replacing all rendering paths at once.
