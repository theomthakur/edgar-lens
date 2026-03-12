"use client";

import { useEffect, useState } from "react";
import {
  createAnalysisJob,
  evaluateReportCitations,
  getAnalysisJob,
} from "@/lib/api";
import { pageTitle } from "@/lib/brand";
import TickerSelect from "@/components/TickerSelect";

function qualityLabel(score: number): "Strong" | "Moderate" | "Weak" {
  if (score >= 0.8) return "Strong";
  if (score >= 0.5) return "Moderate";
  return "Weak";
}

function qualityPillClass(score: number): string {
  if (score >= 0.8) return "bg-emerald-100 text-emerald-700";
  if (score >= 0.5) return "bg-amber-100 text-amber-700";
  return "bg-rose-100 text-rose-700";
}

export default function AnalyzePage() {
  const [ticker, setTicker] = useState("MSFT");
  const [jobId, setJobId] = useState("");
  const [reportId, setReportId] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [qualityScore, setQualityScore] = useState<number | null>(null);
  const [qualityError, setQualityError] = useState("");
  const [qualitySupported, setQualitySupported] = useState<number | null>(null);
  const [qualityTotal, setQualityTotal] = useState<number | null>(null);
  const [agentMode, setAgentMode] = useState("");
  const [agentRounds, setAgentRounds] = useState<number | null>(null);
  const [agentFinalPrecision, setAgentFinalPrecision] = useState<number | null>(null);
  const [agentTargetPrecision, setAgentTargetPrecision] = useState<number | null>(null);
  const [agentLlmEnabled, setAgentLlmEnabled] = useState<boolean | null>(null);
  const [agentLlmUsed, setAgentLlmUsed] = useState<boolean | null>(null);
  const [agentLlmModel, setAgentLlmModel] = useState<string>("");
  const [agentLlmErrors, setAgentLlmErrors] = useState<string[]>([]);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    document.title = pageTitle("Analyze");
  }, []);

  async function runQualityEval(targetReportId: string) {
    setQualityLoading(true);
    setQualityError("");
    try {
      const evalResult = await evaluateReportCitations(targetReportId, 0.2);
      setQualityScore(evalResult.precisionAtThreshold);
      setQualitySupported(evalResult.supportedCitations);
      setQualityTotal(evalResult.totalCitations);
    } catch (err) {
      setQualityScore(null);
      setQualitySupported(null);
      setQualityTotal(null);
      setQualityError(err instanceof Error ? err.message : "Citation evaluation failed.");
    } finally {
      setQualityLoading(false);
    }
  }

  async function startJob(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setQualityScore(null);
    setQualitySupported(null);
    setQualityTotal(null);
    setQualityError("");
    setAgentMode("");
    setAgentRounds(null);
    setAgentFinalPrecision(null);
    setAgentTargetPrecision(null);
    setAgentLlmEnabled(null);
    setAgentLlmUsed(null);
    setAgentLlmModel("");
    setAgentLlmErrors([]);

    try {
      const created = await createAnalysisJob(ticker);
      setJobId(created.jobId);
      setStatus(created.status);
      setAgentMode(created.agentMode ?? "");
      setAgentRounds(created.rounds ?? null);
      setAgentFinalPrecision(created.finalPrecision ?? null);
      setAgentTargetPrecision(created.targetPrecision ?? null);
      setAgentLlmEnabled(created.llmEnabled ?? null);
      setAgentLlmUsed(created.llmUsed ?? null);
      setAgentLlmModel(created.llmModel ?? "");
      setAgentLlmErrors(created.llmErrors ?? []);

      const createdReportId = created.reportId ?? "";
      setReportId(createdReportId);
      if (created.status === "completed" && createdReportId) {
        await runQualityEval(createdReportId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start analysis job.");
    } finally {
      setLoading(false);
    }
  }

  async function refreshStatus() {
    if (!jobId) return;
    const job = await getAnalysisJob(jobId);
    setStatus(job.status);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Run Analysis Job</h1>
      <form className="card p-6 space-y-4" onSubmit={startJob}>
        <TickerSelect value={ticker} onChange={setTicker} />
        <button className="btn-primary" type="submit" disabled={loading}>
          {loading ? "Starting..." : "Start Analysis"}
        </button>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
      </form>

      {jobId ? (
        <section className="card p-6 space-y-3">
          <p className="text-sm">Job ID: {jobId}</p>
          <p className="text-sm">Status: {status}</p>
          {agentMode ? <p className="text-sm">Agent mode: {agentMode}</p> : null}
          {agentRounds !== null ? <p className="text-sm">Agent rounds: {agentRounds}</p> : null}
          {agentFinalPrecision !== null && agentTargetPrecision !== null ? (
            <p className="text-sm">
              Agent precision: {agentFinalPrecision} (target {agentTargetPrecision})
            </p>
          ) : null}
          {agentLlmEnabled !== null ? (
            <p className="text-sm">
              LLM enabled: {String(agentLlmEnabled)} | LLM used: {String(agentLlmUsed)}
              {agentLlmModel ? ` | model: ${agentLlmModel}` : ""}
            </p>
          ) : null}
          {agentLlmErrors.length > 0 ? (
            <p className="text-xs text-amber-700">LLM fallback reason: {agentLlmErrors[0]}</p>
          ) : null}
          <button className="btn-primary" onClick={refreshStatus}>
            Refresh Status
          </button>

          {status === "completed" && reportId ? (
            <div className="rounded border border-slate-200 bg-slate-50 p-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium">Citation Quality (threshold 0.2)</p>
                <button
                  className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100"
                  onClick={() => runQualityEval(reportId)}
                  disabled={qualityLoading}
                >
                  {qualityLoading ? "Checking..." : "Re-check"}
                </button>
              </div>
              {qualityScore !== null ? (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded px-2 py-1 text-xs font-medium ${qualityPillClass(qualityScore)}`}
                  >
                    {qualityLabel(qualityScore)} quality
                  </span>
                  <p>
                    Precision: <span className="font-semibold">{qualityScore}</span>
                    {qualitySupported !== null && qualityTotal !== null
                      ? ` (${qualitySupported}/${qualityTotal} supported)`
                      : ""}
                  </p>
                </div>
              ) : (
                <p className="mt-2 text-slate-600">
                  No score available yet. Run re-check to compute citation quality.
                </p>
              )}
              {qualityError ? <p className="mt-2 text-xs text-red-600">{qualityError}</p> : null}
            </div>
          ) : null}

          {status === "completed" && reportId ? (
            <a className="text-sky-600 underline" href={`/report/${reportId}`}>
              Open Report
            </a>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
