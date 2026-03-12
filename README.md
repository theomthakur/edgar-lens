# EDGAR Lens

A full-stack agentic AI research tool that ingests SEC EDGAR filings, orchestrates multi-round analysis, and produces citation-backed financial reports — with an optional LLM drafting agent.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, App Router |
| Backend | FastAPI (Python), SQLAlchemy |
| Database | PostgreSQL (Docker) / SQLite (local fallback) |
| Data source | SEC EDGAR (public filings) |
| LLM (optional) | OpenAI-compatible API — tested with Ollama (llama3.2), OpenAI |

---

## Features

- **SEC EDGAR Ingestion** — Fetches and chunks the latest 10-K (or other form types) for any public ticker directly from EDGAR. Includes rate-limiting and user-agent compliance enforcement.
- **Agentic Orchestration** — Multi-round analysis loop that drafts a report, self-evaluates citation precision, and adjusts retrieval strategy (`focused` → `broad`) across rounds until a quality target is met.
- **LLM Drafting Agent** — Optional OpenAI-compatible LLM layer. Each orchestration round first attempts LLM-backed generation grounded in SEC excerpts, falling back to a deterministic heuristic if the LLM call fails or is disabled. Tested with Ollama (llama3.2) locally.
- **Citation Evaluation** — Jaccard token-overlap scoring measures how well each report citation is supported by the ingested filing chunks. Aggregate precision is computed and displayed with quality badges.
- **Citation Quality UI** — The Analyze page previews citation quality after every job. The Report page includes a full Citation Quality panel with per-citation support scores and configurable thresholds.
- **Ticker Dropdown** — 36 popular tickers grouped by sector (Technology, Finance, Healthcare, Consumer, Energy, Telecom) with a "custom ticker" fallback for any other symbol.
- **Filing Comparison** — Compare page UI scaffolded (backend logic not yet implemented).

---

## Project Structure

```
.
├── frontend/               # Next.js app
│   ├── app/
│   │   ├── page.tsx        # Home / ingest page
│   │   ├── analyze/        # Run analysis jobs, view agent metadata
│   │   ├── report/[id]/    # View generated report + citation quality panel
│   │   └── compare/        # Side-by-side filing comparison
│   ├── components/
│   │   ├── CitationEvalPanel.tsx
│   │   └── TickerSelect.tsx        # Grouped ticker dropdown (36 tickers + custom)
│   └── lib/
│       ├── api.ts          # Typed API client
│       └── brand.ts        # Branding constants
├── backend/
│   ├── app/
│   │   ├── routers/        # health, filings, analysis, reports, evals
│   │   ├── services/
│   │   │   ├── sec_edgar.py            # EDGAR fetching + compliance
│   │   │   ├── analysis_orchestrator.py # Multi-round agent loop
│   │   │   ├── llm_report_agent.py     # LLM drafting agent
│   │   │   ├── report_builder.py       # Deterministic fallback
│   │   │   └── citation_eval.py        # Jaccard citation scoring
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── persistence.py  # DB read/write helpers
│   │   └── db.py           # Engine + session setup
├── docker-compose.yml
└── .env.example
```

---

## Quickstart

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
- Set `SEC_USER_AGENT` to your real name and email (e.g. `MyApp/1.0 (you@example.com)`). Placeholder values are blocked at runtime.
- Keep `SEC_MIN_REQUEST_INTERVAL_SECONDS` at `0.2` or higher.
- Set `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`.

### 2. Run with Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

### 3. Run locally (without Docker)

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=sqlite:///./finance_agent.db uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

---

## Running with Ollama (Free Local LLM)

```bash
# Install and start Ollama
brew install ollama
ollama pull llama3.2
ollama serve

# Enable in .env
LLM_ENABLED=true
LLM_API_KEY=ollama
LLM_API_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2
```

Then start the backend and frontend as normal. The LLM runs entirely on your machine — no API key or credit card required.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SEC_USER_AGENT` | *(required)* | Must include real contact info, e.g. `App/1.0 (you@example.com)` |
| `SEC_MIN_REQUEST_INTERVAL_SECONDS` | `0.2` | Minimum seconds between EDGAR requests |
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | Backend URL used by the frontend |
| `NEXT_PUBLIC_APP_DISCLAIMER` | — | Optional disclaimer text shown in the footer |
| `DATABASE_URL` | PostgreSQL (Docker) / SQLite (local) | SQLAlchemy connection string |
| `LLM_ENABLED` | `false` | Set to `true` to enable LLM drafting agent |
| `LLM_API_KEY` | — | API key for your LLM provider |
| `LLM_API_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `LLM_MAX_INPUT_CHARS` | `7000` | Character budget for SEC excerpts passed to the LLM |

---

## API Reference

### Filings
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/filings/ingest` | Ingest latest SEC filing for a ticker |

Request body: `{ "ticker": "AAPL", "filingType": "10-K" }`

### Analysis
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/analysis/jobs` | Run analysis job and return report |

Request body: `{ "ticker": "AAPL" }`

Response includes: `reportId`, `agentMode`, `rounds`, `finalPrecision`, `targetPrecision`, `trace`, `llmEnabled`, `llmUsed`, `llmModel`, `llmErrors`

### Reports
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/reports/{reportId}` | Retrieve a generated report with citations |

### Citation Evaluation
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/evals/citations` | Score citation support against filing chunks |

Request body:
```json
{
  "reportId": "report-abc123",
  "filingId": "optional — defaults to latest for ticker",
  "supportThreshold": 0.35
}
```

Response: per-citation Jaccard scores + aggregate `precisionAtThreshold`.

---

## Citation Quality Thresholds

| Badge | Precision |
|---|---|
| Strong | ≥ 0.8 |
| Moderate | 0.5 – 0.79 |
| Weak | < 0.5 |

---

## LLM Agent Mode

Enable in `.env`:
```env
LLM_ENABLED=true
LLM_API_KEY=your-key-here
LLM_MODEL=gpt-4o-mini
```

When enabled, each orchestration round sends the top-ranked SEC excerpts to the LLM with a citation-grounding prompt. The model is instructed to produce JSON containing a `summary` field and a `citations` array sourced only from the provided excerpts. If the LLM call fails, times out, or returns malformed JSON, the pipeline falls back to deterministic report generation automatically — no data is lost.

**Tested providers:**
| Provider | `LLM_API_BASE_URL` | `LLM_MODEL` | Cost |
|---|---|---|---|
| Ollama (local) | `http://localhost:11434/v1` | `llama3.2` | Free |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.1-8b-instant` | Free tier |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | Pay-per-token |

---

## Known Limitations

| Area | Status |
|---|---|
| Compare page | UI is scaffolded — backend YoY diff logic not yet implemented |
| Filing history | Only ingests the **latest** filing; no multi-period support |
| Auth / accounts | No authentication — not suitable for public deployment |
| Report history | No browse/search for past reports in the UI |
| LLM prompt tuning | Prompts are generic; not tuned for analyst-quality financial output |
| Deployment | Local only — no cloud deployment config included |

---

## Legal and Compliance

- SEC EDGAR filings are public records. Access is permitted for research and non-commercial use under SEC fair-access guidelines.
- A valid `SEC_USER_AGENT` header with contact information is required by SEC policy. The backend blocks requests using placeholder values.
- All EDGAR requests are throttled to respect SEC infrastructure.
- This application is for **educational and research purposes only** and does not constitute investment advice.
- If you incorporate third-party data sources (earnings transcripts, news feeds, etc.), verify the applicable license terms independently.