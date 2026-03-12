"use client";

import { useEffect, useState } from "react";
import { ingestLatestFiling } from "@/lib/api";
import { BRAND_DESCRIPTION, BRAND_NAME, BRAND_TAGLINE, pageTitle } from "@/lib/brand";
import TickerSelect from "@/components/TickerSelect";

export default function HomePage() {
  const [ticker, setTicker] = useState("AAPL");
  const [filingType, setFilingType] = useState("10-K");
  const [message, setMessage] = useState<string>("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    document.title = pageTitle("Ingest Filings");
  }, []);

  async function onIngest(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const result = await ingestLatestFiling(ticker, filingType);
      setMessage(
        `Ingested ${result.filingType} for ${result.ticker} filed on ${result.filingDate}.`
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to ingest filing.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-sky-700">{BRAND_TAGLINE}</p>
        <h1 className="mt-2 text-3xl font-semibold">{BRAND_NAME}</h1>
        <p className="mt-2 max-w-3xl text-slate-600">{BRAND_DESCRIPTION}</p>
      </header>

      <section className="card p-6">
        <h2 className="mb-4 text-xl font-medium">Ingest Latest Filing</h2>
        <form className="space-y-4" onSubmit={onIngest}>
          <div className="grid gap-3 md:grid-cols-2">
            <TickerSelect value={ticker} onChange={setTicker} />
            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">Filing Type</label>
              <select
                className="field"
                value={filingType}
                onChange={(e) => setFilingType(e.target.value)}
              >
                <option>10-K</option>
                <option>10-Q</option>
                <option>8-K</option>
              </select>
            </div>
          </div>
          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? "Ingesting..." : "Ingest"}
          </button>
        </form>
        {message ? <p className="mt-4 text-sm text-slate-700">{message}</p> : null}
      </section>

      <section className="grid gap-3 md:grid-cols-3">
        <a className="card p-4 hover:shadow" href="/analyze">
          <h3 className="font-semibold">Run Analysis</h3>
          <p className="text-sm text-slate-600">Start a new analysis job.</p>
        </a>
        <a className="card p-4 hover:shadow" href="/report/demo-report-001">
          <h3 className="font-semibold">View Report</h3>
          <p className="text-sm text-slate-600">Inspect generated report with citations.</p>
        </a>
        <a className="card p-4 hover:shadow" href="/compare">
          <h3 className="font-semibold">Compare Filings</h3>
          <p className="text-sm text-slate-600">See material changes between filings.</p>
        </a>
      </section>
    </div>
  );
}
