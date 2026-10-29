# EDGAR Lens

EDGAR Lens turns public SEC filings into short research briefs with links to the supporting evidence.

**[Try the live demo](https://edgar-lens.vercel.app)**

## What it does

- Fetches a company's latest SEC filing.
- Drafts a brief from relevant filing excerpts.
- Checks citation support and broadens retrieval when evidence is weak.
- Shows the report alongside its sources and citation scores.

## How it works

A Next.js and TypeScript frontend connects to a FastAPI backend. The backend fetches filings from SEC EDGAR, retrieves excerpts, drafts a report, and checks its citations. SQLAlchemy stores the data in PostgreSQL or a local SQLite database.

An OpenAI-compatible model can draft the report. If that is disabled or unavailable, the app uses a deterministic report builder and identifies the generation mode. Citation checks measure text overlap; they do not establish that every claim is correct.

## Run locally

You need Python 3.11+ and Node.js 20.9+.

From the project root:

```bash
cp .env.example .env
```

Set `SEC_USER_AGENT` in `.env` to an application name and your real contact email. Set `LLM_ENABLED=false` to try the deterministic report flow, or configure `LLM_API_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` for model drafting.

Start the backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=sqlite:///./finance_agent.db uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Open [localhost:3000](http://localhost:3000).

## Optional tools

This branch also includes a research agent, Langfuse tracing, and LangChain hybrid retrieval. These integrations are optional; keyword retrieval remains the default.

See the [technical guide](docs/technical-guide.md) for configuration, evaluation results, and API details.
