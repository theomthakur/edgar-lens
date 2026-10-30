# EDGAR Lens

EDGAR Lens reads a public SEC filing, produces a short research brief, and shows the filing excerpts behind its claims.

**Live demo:** [edgar-lens.vercel.app](https://edgar-lens.vercel.app) · **Source:** [GitHub](https://github.com/theomthakur/edgar-lens)

## Why it exists

Company filings are long, and an AI-generated summary can sound convincing even when its evidence is weak. EDGAR Lens keeps the source material beside the answer and measures whether each citation actually supports the text it accompanies.

## What it does

1. Fetches a company's latest filing from SEC EDGAR.
2. Retrieves excerpts relevant to the research question.
3. Drafts a brief from those excerpts.
4. Checks citation support after each draft.
5. Broadens retrieval and tries once more when the evidence is weak.
6. Keeps the better-supported result and makes the evidence inspectable.

The research loop is bounded to two rounds. If model drafting is disabled or unavailable, the same workflow uses a deterministic report builder and clearly identifies that mode.

```text
SEC filing -> retrieve evidence -> draft -> check citations
                                            |
                              strong enough -> finish
                                    weak -> broaden once -> redraft
```

## Technology

- **Interface:** Next.js, React, and TypeScript
- **API:** FastAPI and Python
- **Storage:** PostgreSQL in deployment or SQLite locally
- **Data source:** public SEC EDGAR filings
- **Model:** any OpenAI-compatible endpoint, with a deterministic fallback
- **Observability:** optional Langfuse traces with model usage, cost, retrieval steps, and citation scores

Keyword retrieval remains the default because it performed better in the recorded comparison. An optional LangChain mode combines BM25 with local embeddings through reciprocal-rank fusion. Both modes use the same citation check.

## Verification

- The backend suite covers the agent loop, evaluation, retrieval, tracing, and optional-tooling behavior.
- The optional LangChain test skips cleanly when its extra packages are not installed; with them installed, the full suite contains 39 passing tests.
- A fixed comparison on eight real 10-K filings produced first-round citation precision of **0.875 for keyword retrieval** and **0.749 for hybrid retrieval**. Keyword retrieval was also about three times faster, so it remains the default.
- Langfuse integration was checked with real traces containing retrieval spans, model calls, token usage, estimated cost, and citation scores.

These numbers describe the recorded test set, not every filing or research question.

## Run locally

Use Python 3.11 or newer and Node.js 20.9 or newer.

```bash
cp .env.example .env
```

Set `SEC_USER_AGENT` to an application name and a real contact email. To run without a model provider, set `LLM_ENABLED=false`. To enable model drafting, configure `LLM_API_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY`.

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

Open [localhost:3000](http://localhost:3000). Docker Compose is also available:

```bash
docker compose up --build
```

## Limits

- Citation scoring measures textual support. It does not prove that a financial interpretation is correct.
- Hybrid retrieval is optional and requires additional local packages.
- The application is a research aid, not investment advice, and it does not trade or place orders.
- The live demo depends on the availability and rate limits of SEC EDGAR and the configured model provider.

See the [technical guide](docs/technical-guide.md) for configuration, evaluation details, tracing, retrieval modes, and API documentation.

Built by [Om Thakur](https://theomthakur.github.io/portfolio) · [LinkedIn](https://www.linkedin.com/in/theomthakur/)
