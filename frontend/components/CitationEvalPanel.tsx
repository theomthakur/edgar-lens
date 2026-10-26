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
    <section className="border border-[#163f34] bg-[#163f34] p-6 text-white sm:p-8">
      <div className="grid gap-6 sm:grid-cols-[1fr_auto] sm:items-end">
        <div>
          <p className="eyebrow text-[#d8f56a]">Independent check</p>
          <h2 className="display mt-3 text-3xl">Do the citations support the report?</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-white/70">
            Run the deterministic citation check to compare every quoted excerpt with the ingested filing chunks.
          </p>
        </div>
        <button className="border border-[#d8f56a] bg-[#d8f56a] px-5 py-3 text-sm font-bold text-[#14251f] disabled:opacity-50" onClick={runEvaluation} disabled={loading}>
          {loading ? "Checking evidence" : data ? "Check again" : "Check the evidence"}
        </button>
      </div>

      {error ? <p className="mt-5 border border-[#b65d55] bg-[#b65d55]/20 p-4 text-sm">{error}</p> : null}

      {data ? (
        <div className="mt-8 border-t border-white/15 pt-7">
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <p className="metric-number text-5xl text-[#d8f56a]">{Math.round(data.precisionAtThreshold * 100)}%</p>
              <p className="mt-1 text-xs uppercase tracking-[0.14em] text-white/55">citation precision</p>
            </div>
            <div>
              <p className="metric-number text-5xl">{data.supportedCitations}/{data.totalCitations}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.14em] text-white/55">citations supported</p>
            </div>
            <div>
              <p className="metric-number text-2xl">{qualityLabel(data.precisionAtThreshold)}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.14em] text-white/55">release signal</p>
            </div>
          </div>

          <ol className="mt-8 space-y-3">
            {data.results.map((item, index) => (
              <li className="border border-white/15 bg-white/[0.04] p-4" key={item.citationId}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm font-bold">{index + 1}. {item.section}</p>
                  <span className={`px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-[0.12em] ${item.supported ? "bg-[#d8f56a] text-[#14251f]" : "bg-[#d99b35] text-[#14251f]"}`}>
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
