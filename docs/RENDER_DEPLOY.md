# Render deployment

The repository root contains a Dockerfile and `render.yaml`. The Docker image builds the React UI and serves it from FastAPI on the same origin as `/api`. PubMed and Europe PMC are queried live by the backend. The evaluation corpora are offline benchmark files, not an API service; they are intentionally excluded from the image.

## Create the service

1. Commit the deployment files when the team approves them. Render builds from a Git revision, so uncommitted local changes cannot appear on the deployed site.
2. In Render, choose **New → Blueprint** and connect this repository. It defines one free web service and one free Postgres database.
3. Enter `NCBI_EMAIL` (an actual team contact address) and `NCBI_API_KEY` in Render's secret-variable prompts. The key is optional for correctness but raises NCBI's request limit. Do not place either value in source control or in a `VITE_` variable.
4. Wait for `/api/health` to report a healthy database. Open the service URL and enter the workspace. Create a review and run a small live PubMed search; repeat with Europe PMC.

The Docker start command applies Alembic migrations before serving requests. The frontend uses the same-origin `/api` path. Render injects `DATABASE_URL` from its managed Postgres instance; the app selects the installed psycopg driver.

Render's free Postgres database expires after 30 days. Move to a paid database before treating it as lasting storage. The prepared local checkpoint review lives in the local SQLite database and is **not** automatically copied into Render Postgres; on the hosted app, create a fresh review and import live results. Never upload the raw evaluation corpora to the service.
