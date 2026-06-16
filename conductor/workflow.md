# Workflow — karusel_bot

## Development Loop

1. **Spec** — write or update `conductor/tracks/<track_id>/spec.md` before any code.
2. **Plan** — break the work into ordered, verifiable tasks in `plan.md`.
3. **Implement** — execute the plan. Run tests after each meaningful change.
4. **Verify** — `rtk pytest` must pass before declaring done.
5. **Commit** — conventional commits; small, focused diffs.
6. **Ship** — only after explicit user approval: deploy via `rtk ssh` + `docker compose`.

## Branch Strategy

- `main` is the production branch.
- All work happens in place on `main` unless the user asks for a worktree/branch.
- Uncommitted changes must be preserved across handoffs.

## Testing Discipline

- Unit tests in `tests/` use `unittest`.
- AST-based tests in `tests/test_flow_structure.py` assert that specific symbols/strings exist in source files.
- Behavior tests assert on rendered HTML, data URLs, and exports.
- Always run `rtk pytest tests/<new_test_file>.py` first, then the full suite.

## Code Style

- Keep modules small and single-purpose.
- `services/` modules export pure functions where possible; handlers orchestrate.
- Reuse existing helpers (`asdict`, `load_export_package`, `get_export_package`, `image_bytes_to_data_url`) before adding new ones.
- New renderers must be wrapped in `asyncio.to_thread(...)` from async handlers.
- No new runtime dependencies without a written justification in the track spec.

## Production-Only Changes

- Production server: `root@5.253.188.164` → `/root/karusel_bot_v2` → container `karusel_bot_new`.
- The bot image bakes the code via `COPY . .` in `Dockerfile`. **Code is NOT mounted** into the running container — only `./data:/app/data` is. So **a `docker compose restart` is NOT enough** to pick up code changes; the image must be rebuilt and the container recreated.
- Deploy only after user explicit "go ahead". Use the **rebuild sequence**:
  ```bash
  # 1. Copy changed source files to the host.
  rtk sh -c 'cat <local_file> | ssh root@5.253.188.164 "cat > /root/karusel_bot_v2/<remote_path>"'
  # Repeat for every changed file. Do NOT rely on `restart`.
  # 2. Stop, rebuild, and recreate the container (this is the only step that actually applies code).
  rtk ssh root@5.253.188.164 'cd /root/karusel_bot_v2 && docker compose down bot && docker compose up -d --build bot'
  # 3. Verify: imports resolve, polling started, no traceback.
  rtk ssh root@5.253.188.164 'cd /root/karusel_bot_v2 && docker compose logs --tail=100 bot'
  rtk ssh root@5.253.188.164 'cd /root/karusel_bot_v2 && docker compose exec bot python -c "from utils.states import TestRenderFlow; print(TestRenderFlow.waiting_for_text.state)"'
  ```
- `docker compose restart bot` looks like it works but silently keeps the **previous** image. Always use `down + up -d --build`.
- Never `rsync`. Never commit secrets.

## Handoff Discipline

- When a session ends mid-work, leave a `HANDOFF_*.md` file in repo root with: what was done, what's uncommitted, what's next, and any non-obvious decisions.
- The next agent reads the handoff first.
