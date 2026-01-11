# Job Filler Agent (AutoApply Agent)

An AI‑agentic job application assistant focused on a few popular portals (Workday first, Greenhouse/Lever next). It combines a FastAPI backend for profile/resume intelligence with a Chrome side‑panel extension that extracts job context, generates structured fill packets, and executes best‑effort form fills on supported portals.

## What it does

- Reads job context from the current page (JD, title, company hints).
- Runs an agentic loop to build a fill packet and decision data.
- Generates structured outputs:
  - Screening answers
  - Short cover letter
  - One‑liner
  - Resume keywords
  - Packet fields (location, work auth, notice period, etc.)
- Stores user profiles, resumes, and application history in Postgres.
- Executes a Workday‑focused Apply + Fill flow (best‑effort, no auto‑submit).
- Handles resume/photo uploads via guided file picker + auto‑continue.

## Tech stack

- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic
- DB: Postgres (Docker-friendly)
- Vector search (planned): pgvector or external vector DB
- Extension: Chrome MV3 side panel, content scripts, vanilla JS/HTML/CSS

## Project layout

- `app/` FastAPI app, routers, services, models
- `alembic/` migrations
- `job-filler-extension/` Chrome extension (panel + content script)
- `scripts/` helper scripts

## Agentic workflow (high‑level)

The backend orchestrator runs a Think → Act → Observe → Decide loop and keeps state, observations, and actions. The flow is intentionally narrow and deterministic so it’s reliable for demos:

1) **Plan** next tool call based on current state  
2) **Act** using tools (profile, mapping, drafting, analysis)  
3) **Observe** results + update state  
4) **Decide** next step or stop  

This is designed to be extended later with richer tools and reasoning.

## Run locally

### 1) Start Postgres (Docker)

If you use the provided Docker config:

```bash
docker compose up -d
```

Confirm the Postgres port (common: `5433` mapped to container `5432`):

```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"
```

### 2) Set DATABASE_URL

Update `.env` or export it before running:

```bash
export DATABASE_URL=postgresql+psycopg://autoapply:autoapply@localhost:5433/job_filler
```

### 3) Run migrations

```bash
python -m alembic upgrade head
```

### 4) Start the API

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open docs: `http://127.0.0.1:8000/docs`

## Extension setup

1) Open `chrome://extensions` and enable Developer mode.
2) Click "Load unpacked" and select `job-filler-extension/`.
3) Open a supported job page and open the side panel.

### Recommended flow

1) Upload resume in the extension (Resume Upload card).
2) Use Apply + Fill (Beta) on a Workday job page.
3) When file picker opens, select your file.
4) The extension will auto-continue after the upload completes.

## Key endpoints

- Auth: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`
- Profile: `GET /profile/get`, `PUT /profile/update`
- Resume: `POST /resume/upload`
- GitHub: `POST /github/connect`, `POST /github/sync`
- Job analysis: `POST /job/analyse`
- Agent: `POST /agent/run`, `POST /agent/continue`
- Applications: `POST /application/log`, `GET /application/log`
- Fill packet: `POST /agent/fill_packet`

## Data model (Postgres)

- `users`: id, name, email, hashed_password, created_at
- `resumes`: id, user_id, resume_type, filename, uploaded_at, parsed_json
- `projects` / `experiences`: id, user_id, title, description, tech_stack, metrics, source, created_at
- `applications`: id, user_id, company, job_title, job_url, applied_at, used_resume_id, fit_score, status
- `answers`: id, application_id, question_text, answer_text, char_limit, edited_by_user
- `user_settings`: id, user_id, default_tone, default_resume_type, default_location, notification_preferences
- `user_facts`: id, user_id, key, value, source, last_confirmed_at, created_at, updated_at
- `agent_runs`, `agent_step_logs` for audit trails

## Local configuration tips

- If you use Docker for Postgres, ensure `DATABASE_URL` points to the mapped port (often `5433`).
- If profile fetch returns 500, the DB is not reachable or URL is wrong.

## Supported portals (demo scope)

- Workday (primary)
- Greenhouse (planned)
- Lever (planned)

This project is intentionally scoped to a few portals for reliability and recruiter-friendly demos. It does not attempt to auto-apply across all websites.

## Notes

- The Workday flow is best-effort and may require manual steps (captchas, file pickers).
- The extension does not auto-submit final applications.
- Vector search is scaffolded; plug in pgvector or another vector DB as needed.

## License

MIT (update if you need a different license).
