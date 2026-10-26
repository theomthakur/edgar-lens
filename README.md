# EDGAR Lens

EDGAR Lens reads a public SEC filing, drafts a short research brief, and shows the evidence behind every result.

**Live demo:** https://edgar-lens.vercel.app

The important part is the loop: it drafts from filing excerpts, checks whether the citations support the output, and broadens retrieval only when the evidence is weak. It stops after two rounds and keeps the best-supported result. It does not trade, place orders, or provide investment advice.

## What you can do

1. Choose a public company and filing type.
2. Pull the latest filing directly from SEC EDGAR.
3. Follow the research trace as the system drafts and verifies the report.
4. Open the finished brief and inspect each cited excerpt.
5. Run the citation check again from the report page.

The homepage also includes a sample report, so the product can be explored without waiting for a new filing to be ingested.

## How the research loop works

```text
SEC filing -> retrieve excerpts -> draft -> verify citations
                                           |
                           strong evidence -> stop
                             weak evidence -> broaden retrieval -> try once more
```

The flexible step is deliberately bounded. Citation scoring, the two-round limit, fallback behavior, and the stop condition are deterministic and visible.

LLM drafting is optional. When it is disabled or unavailable, the same workflow uses a deterministic report builder rather than failing silently. The API response identifies which generation mode was used in every round.

## Stack

- Next.js, React, TypeScript, and Tailwind CSS
- FastAPI, SQLAlchemy, and PostgreSQL
- SEC EDGAR as the public data source
- Any OpenAI-compatible model as an optional drafting layer

## Run it locally

Use Node 20.9 or newer and Python 3.11 or newer.

```bash
cp .env.example .env
```

Set `SEC_USER_AGENT` to an application name and a real contact email. SEC requests with placeholder contact information are rejected by the app.

Start the backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=sqlite:///./finance_agent.db uvicorn app.main:app --reload
```

Start the frontend in another terminal:

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Then open `http://localhost:3000`.

You can also run the full stack with Docker:

```bash
docker compose up --build
```

## Configuration

| Variable | Purpose |
|---|---|
| `SEC_USER_AGENT` | Required contact identifier for SEC EDGAR requests |
| `SEC_MIN_REQUEST_INTERVAL_SECONDS` | Delay between SEC requests; defaults to `0.2` |
| `DATABASE_URL` | PostgreSQL URL in production, or SQLite locally |
| `NEXT_PUBLIC_API_BASE_URL` | Public backend URL used by the frontend |
| `LLM_ENABLED` | Enables the optional LLM drafting step |
| `LLM_API_KEY` | Key for an OpenAI-compatible provider |
| `LLM_API_BASE_URL` | Provider endpoint |
| `LLM_MODEL` | Model used for drafting |
| `LLM_MAX_INPUT_CHARS` | Maximum filing context sent to the model |

For local Ollama, set `LLM_ENABLED=true`, use `http://localhost:11434/v1` as the base URL, and choose a locally installed model. No LLM configuration is required for the deterministic fallback.

## API

| Method | Endpoint | What it does |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/filings/ingest` | Ingest the latest filing for a ticker |
| `POST` | `/api/analysis/jobs` | Run the bounded research loop |
| `GET` | `/api/analysis/jobs/{job_id}` | Read job status |
| `GET` | `/api/reports/{report_id}` | Retrieve a cited report |
| `POST` | `/api/evals/citations` | Re-score report citations against filing chunks |

Example:

```json
POST /api/filings/ingest
{
  "ticker": "AAPL",
  "filingType": "10-K"
}
```

The analysis response includes the number of rounds, retrieval strategy, generation mode, citation count, and citation precision for each round.

## Verification

```bash
cd backend && .venv/bin/pytest -q
cd frontend && npm run build
cd frontend && npm audit --omit=dev
```

The backend test suite covers ingestion helpers, report generation, citation checks, and the bounded agent loop. The frontend build performs the production TypeScript and route checks.

## Current boundaries

- The app analyzes the latest filing rather than a full filing history.
- Citation support uses deterministic token-overlap scoring. It is a release signal, not a substitute for analyst review.
- There are no user accounts. This is a focused research demo, not a multi-tenant product.
- Public deployments should use PostgreSQL. SQLite is intended only for local development.

## Responsible use

EDGAR Lens uses public filings and follows SEC request throttling and user-agent requirements. Reports are research support only. Always inspect the cited source before relying on a generated statement.
