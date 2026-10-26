"use client";

import { useState } from "react";
import { type CitationEvalResponse, evaluateReportCitations } from "@/lib/api";

type Props = { reportId: string };

function qualityLabel(score: number) {
  if (score >= 0.8) return "Strong support";
  if (score >= 0.5) return "Needs review";
  return "Weak support";
}

export default function CitationEvalPanel({ reportId }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState<CitationEvalResponse | null>(null);

  async function runEvaluation() {
    setLoading(true);
    setError("");
    try {
      setData(await evaluateReportCitations(reportId, 0.2));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Citation evaluation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-xl border border-[#172033] bg-[#172033] p-6 text-white sm:p-7">
      <div className="grid gap-6 sm:grid-cols-[1fr_auto] sm:items-end">
        <div>
          <p className="text-sm font-medium text-blue-200">Independent check</p>
          <h2 className="display mt-2 text-2xl">Do the citations support the report?</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-white/70">
            Run the deterministic citation check to compare every quoted excerpt with the ingested filing chunks.
          </p>
        </div>
        <button className="rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-[#172033] transition hover:bg-blue-50 disabled:opacity-50" onClick={runEvaluation} disabled={loading}>
          {loading ? "Checking evidence" : data ? "Check again" : "Check the evidence"}
        </button>
      </div>

      {error ? <p className="mt-5 rounded-lg border border-red-300 bg-red-500/20 p-4 text-sm">{error}</p> : null}

      {data ? (
        <div className="mt-8 border-t border-white/15 pt-7">
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <p className="metric-number text-4xl text-white">{Math.round(data.precisionAtThreshold * 100)}%</p>
              <p className="mt-1 text-xs text-white/55">citation precision</p>
            </div>
            <div>
              <p className="metric-number text-5xl">{data.supportedCitations}/{data.totalCitations}</p>
              <p className="mt-1 text-xs text-white/55">citations supported</p>
            </div>
            <div>
              <p className="metric-number text-2xl">{qualityLabel(data.precisionAtThreshold)}</p>
              <p className="mt-1 text-xs text-white/55">release signal</p>
            </div>
          </div>

          <ol className="mt-8 space-y-3">
            {data.results.map((item, index) => (
              <li className="rounded-lg border border-white/15 bg-white/[0.04] p-4" key={item.citationId}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm font-bold">{index + 1}. {item.section}</p>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${item.supported ? "bg-blue-200 text-[#172033]" : "bg-amber-200 text-[#172033]"}`}>
                    {item.supported ? "Supported" : "Review"} · {Math.round(item.supportScore * 100)}%
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-white/70">Best source match: {item.bestMatchExcerpt}</p>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </section>
  );
}
