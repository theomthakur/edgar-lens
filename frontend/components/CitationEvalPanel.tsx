"use client";

import { useState } from "react";
import { CitationEvalResponse, evaluateReportCitations } from "@/lib/api";

type Props = {
  reportId: string;
};

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

export default function CitationEvalPanel({ reportId }: Props) {
  const [threshold, setThreshold] = useState(0.35);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState<CitationEvalResponse | null>(null);

  async function runEvaluation() {
    setLoading(true);
    setError("");
    try {
      const result = await evaluateReportCitations(reportId, threshold);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to evaluate citations.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card p-6 space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-lg font-medium">Citation Quality</h2>
          <p className="text-sm text-slate-600">
            Evaluate whether report citations are supported by ingested filing chunks.
          </p>
        </div>

        <div className="flex items-end gap-2">
          <label className="text-sm">
            Threshold
            <input
              className="field mt-1 w-24"
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
            />
          </label>
          <button className="btn-primary" onClick={runEvaluation} disabled={loading}>
            {loading ? "Evaluating..." : "Run Eval"}
          </button>
        </div>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {data ? (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded border p-3">
              <p className="text-xs text-slate-500">Precision @ threshold</p>
              <p className="text-xl font-semibold">{data.precisionAtThreshold}</p>
              <span
                className={`mt-2 inline-block rounded px-2 py-1 text-xs font-medium ${qualityPillClass(
                  data.precisionAtThreshold
                )}`}
              >
                {qualityLabel(data.precisionAtThreshold)} quality
              </span>
            </div>
            <div className="rounded border p-3">
              <p className="text-xs text-slate-500">Supported</p>
              <p className="text-xl font-semibold">{data.supportedCitations}</p>
            </div>
            <div className="rounded border p-3">
              <p className="text-xs text-slate-500">Total citations</p>
              <p className="text-xl font-semibold">{data.totalCitations}</p>
            </div>
            <div className="rounded border p-3">
              <p className="text-xs text-slate-500">Filing</p>
              <p className="text-sm font-medium">{data.filingId}</p>
            </div>
          </div>

          <ul className="space-y-3">
            {data.results.map((item) => (
              <li key={item.citationId} className="rounded border p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{item.section}</p>
                  <span
                    className={`rounded px-2 py-1 text-xs ${
                      item.supported
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {item.supported ? "Supported" : "Weak support"}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">Score: {item.supportScore}</p>
                <p className="mt-2 text-sm text-slate-700">Best match: {item.bestMatchExcerpt}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
