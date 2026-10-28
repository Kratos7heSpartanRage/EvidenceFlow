# Deploying EvidenceFlow on Render

This guide provides step-by-step instructions to deploy EvidenceFlow (Backend, Frontend, and PostgreSQL Database) on [Render.com](https://render.com).

---

## Architecture on Render

EvidenceFlow runs on Render using three synchronized components:

1. **PostgreSQL Database (`evidenceflow-db`)**: Managed database with automatic backups and persistence.
2. **Backend API (`evidenceflow-backend`)**: Python 3 FastAPI service with Alembic auto-migrations.
3. **Frontend UI (`evidenceflow-frontend`)**: Fast global CDN static site built with Vite & React.

---

## Method 1: 1-Click Blueprint Deployment (Recommended)

Because the repository includes `render.yaml`, Render can set up all three services automatically:

1. Push your latest code to GitHub:
   ```bash
   git add .
   git commit -m "chore: configure Render production deployment"
   git push origin main
   ```
2. Log in to your [Render Dashboard](https://dashboard.render.com).
3. Click **New +** in the top navigation bar and select **Blueprint**.
4. Connect your **evidenceflow** GitHub repository.
5. Render will automatically read `render.yaml` and display:
   - Database: `evidenceflow-db` (PostgreSQL)
   - Web Service: `evidenceflow-backend` (FastAPI)
   - Static Site: `evidenceflow-frontend` (Vite SPA)
6. Click **Apply**.
7. Wait 2–3 minutes for the build to finish. Render will provide your public URLs!

---

## Method 2: Manual Setup (If preferred)

### Step 1: Create the Database
1. Go to **New +** → **PostgreSQL**.
2. Name: `evidenceflow-db`
3. Database: `evidenceflow`
4. User: `evidenceflow`
5. Plan: **Free** (or Starter)
6. Click **Create Database**.
7. Copy the **Internal Database URL** (e.g. `postgres://evidenceflow:pass@dpg-xxx/evidenceflow`).

### Step 2: Create the Backend Web Service
1. Go to **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure settings:
   - **Name**: `evidenceflow-backend`
   - **Runtime**: `Python 3`
   - **Branch**: `main`
   - **Build Command**: `pip install -r backend/requirements.txt && alembic -c backend/alembic.ini upgrade head`
   - **Start Command**: `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/api/health`
4. Add **Environment Variables**:
   - `PYTHONPATH`: `backend`
   - `DATABASE_URL`: *(paste the Internal Database URL from Step 1)*
   - `NCBI_EMAIL`: `your-email@domain.com`
   - `NCBI_TOOL`: `evidenceflow`
   - `ENVIRONMENT`: `production`
5. Click **Create Web Service**.
6. Copy your live backend URL (e.g. `https://evidenceflow-backend.onrender.com`).

### Step 3: Create the Frontend Static Site
1. Go to **New +** → **Static Site**.
2. Connect your GitHub repository.
3. Configure settings:
   - **Name**: `evidenceflow-frontend`
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
4. Add **Environment Variable**:
   - `VITE_API_BASE_URL`: `https://evidenceflow-backend.onrender.com/api`
5. Add **Rewrite Rule** (for client-side routing):
   - In your static site dashboard, go to **Redirects/Rewrites**.
   - **Source**: `/*`
   - **Destination**: `/index.html`
   - **Action**: `Rewrite`
6. Click **Create Static Site**.

---

## Verification Checklist

Once deployed:
1. Open the backend health endpoint: `https://<backend-url>/api/health`. It should return `{"status":"ok","database":"healthy"}`.
2. Open the Swagger API docs: `https://<backend-url>/docs`.
3. Open the frontend: `https://<frontend-url>/`.
4. Check the top header in the UI: The green badge should say **Backend Live**.
5. Test creating a review or running a literature query!

