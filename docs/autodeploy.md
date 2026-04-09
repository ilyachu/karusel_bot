## Autodeploy

This repo now includes a GitHub Actions deploy workflow:

- trigger: push to `main`
- deploy method: `rsync` project files to the server
- restart method: `docker compose up -d --build`

### Expected GitHub secrets

- `DEPLOY_SERVER_HOST`
- `DEPLOY_SERVER_USER`
- `DEPLOY_SERVER_PASSWORD`
- `DEPLOY_SERVER_PATH`

### Notes

- `.env` stays on the server and is not overwritten by deploys
- `data/` stays on the server and is not overwritten by deploys
- deployment is currently server-password based for speed; move to SSH key auth later if you want a cleaner setup
