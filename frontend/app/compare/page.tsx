"use client";

import { useEffect, useState } from "react";
import { compareFilings } from "@/lib/api";
import { pageTitle } from "@/lib/brand";

export default function ComparePage() {
  const [ticker, setTicker] = useState("NVDA");
  const [current, setCurrent] = useState("filing-2025-q4");
  const [previous, setPrevious] = useState("filing-2024-q4");
  const [highlights, setHighlights] = useState<string[]>([]);

  useEffect(() => {
    document.title = pageTitle("Compare Filings");
  }, []);

  async function onCompare(e: React.FormEvent) {
    e.preventDefault();
    const res = await compareFilings(ticker, current, previous);
    setHighlights(res.highlights);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Compare Filings</h1>
      <form className="card p-6 grid gap-3" onSubmit={onCompare}>
        <input className="field" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
        <input className="field" value={current} onChange={(e) => setCurrent(e.target.value)} />
        <input className="field" value={previous} onChange={(e) => setPrevious(e.target.value)} />
        <button className="btn-primary" type="submit">Compare</button>
      </form>

      {highlights.length > 0 ? (
        <section className="card p-6">
          <h2 className="mb-2 text-lg font-medium">Material Changes</h2>
          <ul className="list-disc pl-6 text-sm text-slate-700">
            {highlights.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
