## Autodeploy

Autodeploy is intentionally not shipped in the public repository.

The project can be deployed with any private CI/CD setup that:
- syncs project files to the server
- preserves server-owned `.env`
- preserves server-owned `data/`
- runs `docker compose up -d --build`

### Recommended private CI secrets

- `DEPLOY_SERVER_HOST`
- `DEPLOY_SERVER_USER`
- `DEPLOY_SSH_PRIVATE_KEY`
- `DEPLOY_SERVER_PATH`

### Notes

- `.env` stays on the server and is not overwritten by deploys
- `data/` stays on the server and is not overwritten by deploys
- use SSH key auth for public repositories
- do not put server passwords into public repository workflows
