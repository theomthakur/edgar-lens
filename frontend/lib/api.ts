export type IngestResponse = {
  ticker: string;
  filingType: string;
  filingDate: string;
  status: string;
};

export type JobResponse = {
  jobId: string;
  status: string;
  reportId?: string;
  agentMode?: string;
  rounds?: number;
  finalPrecision?: number;
  targetPrecision?: number;
  llmEnabled?: boolean;
  llmUsed?: boolean;
  llmModel?: string | null;
  llmErrors?: string[];
  trace?: Array<{
    round: number;
    strategy: string;
    generationMode?: string;
    citationCount: number;
    precision: number;
  }>;
};

export type Citation = {
  sourceTitle: string;
  section: string;
  excerpt: string;
};

export type ReportResponse = {
  reportId: string;
  ticker: string;
  summary: string;
  keyFindings: string[];
  citations: Citation[];
};

export type CitationEvalResult = {
  citationId: number;
  section: string;
  sourceTitle: string;
  supportScore: number;
  supported: boolean;
  bestMatchExcerpt: string;
};

export type CitationEvalResponse = {
  reportId: string;
  ticker: string;
  filingId: string;
  supportThreshold: number;
  totalCitations: number;
  supportedCitations: number;
  precisionAtThreshold: number;
  results: CitationEvalResult[];
};

function resolveApiBaseUrl(): string {
  const raw =
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
    "http://127.0.0.1:8000";

  // Avoid IPv6 localhost (::1) resolution differences in local dev.
  return raw.replace("http://localhost:", "http://127.0.0.1:");
}

const API_BASE = resolveApiBaseUrl();

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const payload = (await res.json()) as { detail?: string };
      throw new Error(payload.detail || `Request failed: ${res.status}`);
    }

    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }

  return res.json() as Promise<T>;
}

export function ingestLatestFiling(ticker: string, filingType: string) {
  return fetchJson<IngestResponse>("/api/filings/ingest", {
    method: "POST",
    body: JSON.stringify({ ticker, filingType }),
  });
}

export function createAnalysisJob(ticker: string) {
  return fetchJson<JobResponse>("/api/analysis/jobs", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  });
}

export function getAnalysisJob(jobId: string) {
  return fetchJson<JobResponse>(`/api/analysis/jobs/${jobId}`);
}

export function getReport(reportId: string) {
  return fetchJson<ReportResponse>(`/api/reports/${reportId}`);
}

export function compareFilings(ticker: string, current: string, previous: string) {
  return fetchJson<{ ticker: string; highlights: string[] }>("/api/analysis/compare", {
    method: "POST",
    body: JSON.stringify({ ticker, currentFilingId: current, previousFilingId: previous }),
  });
}

export function evaluateReportCitations(reportId: string, supportThreshold = 0.35) {
  return fetchJson<CitationEvalResponse>("/api/evals/citations", {
    method: "POST",
    body: JSON.stringify({ reportId, supportThreshold }),
  });
}
