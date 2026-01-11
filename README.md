# Job Filler Agent API

FastAPI backend scaffold for an automatic job application filler. All endpoints are stubbed with in-memory state for quick iteration.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open docs at http://localhost:8000/docs

## Available endpoints
- `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`
- `GET /profile/get`, `PUT /profile/update`
- `POST /resume/upload`
- `POST /github/connect`, `POST /github/sync`
- `POST /job/analyse`
- `POST /agent/run`
- `POST /application/log`, `GET /application/log`

State persists in memory only. Replace services with real storage/LLM integrations as you build features.

## Data model (Postgres)

- `users`: id, name, email, hashed_password, created_at
- `resumes`: id, user_id, resume_type, filename, uploaded_at, parsed_json
- `projects` / `experiences`: id, user_id, title, description, tech_stack, metrics, source, created_at
- `applications`: id, user_id, company, job_title, job_url, applied_at, used_resume_id, fit_score, status
- `answers`: id, application_id, question_text, answer_text, char_limit, edited_by_user
- `user_settings`: id, user_id, default_tone, default_resume_type, default_location, notification_preferences

SQLAlchemy models are defined in `app/models/db_models.py`; configure `DATABASE_URL` via env (defaults to local Postgres).

## Vector search plan

Use a vector DB (pgvector/Pinecone/etc.) to index:
- Project/experience bullets (JD ↔ relevant work)
- Resume summaries (auto-select best resume)
- Past Q&A (reuse/adapt answers)

`app/services/vector_store.py` and `app/services/recommendations.py` hold stubs to swap in a real vector client and embedding calls.
