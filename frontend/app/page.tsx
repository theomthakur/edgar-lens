"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import TickerSelect from "@/components/TickerSelect";
import {
  createAnalysisJob,
  evaluateReportCitations,
  ingestLatestFiling,
  type JobResponse,
} from "@/lib/api";

type Phase = "idle" | "ingesting" | "analyzing" | "verifying" | "complete" | "error";

const steps = [
  { key: "ingesting", title: "Read the filing", copy: "Fetch the latest public filing from SEC EDGAR." },
  { key: "analyzing", title: "Draft with evidence", copy: "Build a report from the most relevant filing sections." },
  { key: "verifying", title: "Test every citation", copy: "Score whether each cited excerpt supports the generated claim." },
  { key: "complete", title: "Adapt or finish", copy: "Broaden retrieval when support is weak, then keep the best round." },
] as const;

const phaseOrder: Phase[] = ["idle", "ingesting", "analyzing", "verifying", "complete"];

export default function HomePage() {
  const [ticker, setTicker] = useState("AAPL");
  const [filingType, setFilingType] = useState("10-K");
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState("");
  const [job, setJob] = useState<JobResponse | null>(null);
  const [citationScore, setCitationScore] = useState<number | null>(null);
  const [supported, setSupported] = useState<{ count: number; total: number } | null>(null);

  const activeIndex = useMemo(() => phaseOrder.indexOf(phase), [phase]);
  const running = !["idle", "complete", "error"].includes(phase);

  async function runResearch(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setJob(null);
    setCitationScore(null);
    setSupported(null);

    try {
      setPhase("ingesting");
      await ingestLatestFiling(ticker, filingType);

      setPhase("analyzing");
      const created = await createAnalysisJob(ticker);
      setJob(created);

      if (!created.reportId) {
        throw new Error("The analysis finished without a report. Please try again.");
      }

      setPhase("verifying");
      const evaluation = await evaluateReportCitations(created.reportId, 0.2);
      setCitationScore(evaluation.precisionAtThreshold);
      setSupported({ count: evaluation.supportedCitations, total: evaluation.totalCitations });
      setPhase("complete");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The research run could not be completed.");
      setPhase("error");
    }
  }

  return (
    <>
      <section className="border-b rule">
        <div className="mx-auto grid max-w-6xl gap-12 px-5 py-16 lg:grid-cols-[1.15fr_0.85fr] lg:px-8 lg:py-20">
          <div>
            <p className="eyebrow text-[#355f9e]">Public-company research / SEC EDGAR</p>
            <h1 className="display mobile-hero-title mt-5 max-w-3xl text-[3.25rem] leading-[0.98] sm:text-[4.35rem] lg:text-[5rem]">
              Don’t just read
              <br />
              <span className="italic text-[#a64b3c]">the conclusion.</span>
            </h1>
            <p className="mt-7 max-w-2xl text-lg leading-8 text-[#657080]">
              EDGAR Lens is a reading desk for public filings. It creates a concise brief, then leaves the source trail
              visible so the conclusion can be challenged, checked, or trusted for the right reason.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a className="btn-primary mobile-action" href="#research">Run a filing analysis <span aria-hidden="true">→</span></a>
              <Link className="btn-secondary mobile-action" href="/report/demo-report-001">Explore a sample report</Link>
            </div>
          </div>

          <div className="archive-panel ledger-card lg:self-center p-6 sm:p-8">
            <div className="flex items-center justify-between gap-4 border-b rule pb-4">
              <p className="eyebrow text-[#657080]">Research ledger / 01</p>
              <span className="signal-tag">Visible reasoning</span>
            </div>
            <div className="mt-6 space-y-6">
              {[
                ["A", "Locate", "Start with the actual filing, not a secondary summary."],
                ["B", "Annotate", "Turn relevant excerpts into a reviewable brief."],
                ["C", "Challenge", "Test whether each citation earns the claim beside it."],
                ["D", "Conclude", "Widen the search only when the evidence asks for it."],
              ].map(([number, title, copy]) => (
                <div className="grid grid-cols-[2rem_1fr] gap-4" key={number}>
                  <span className="metric-number text-lg text-[#a64b3c]">{number}</span>
                  <div>
                    <p className="font-bold">{title}</p>
                    <p className="mt-1 text-sm leading-6 text-[#657080]">{copy}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="research" className="mx-auto max-w-6xl px-5 py-16 lg:px-8 lg:py-20">
        <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
          <div>
            <p className="eyebrow text-[#355f9e]">Open a filing</p>
            <h2 className="display mt-4 text-4xl leading-tight sm:text-5xl">Start a fresh research note.</h2>
            <p className="mt-5 max-w-lg leading-7 text-[#657080]">
              The source is fetched from SEC EDGAR. The resulting brief is research support, not investment advice.
            </p>

            <div className="mt-8 border-y rule py-5">
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div><p className="metric-number text-2xl">2</p><p className="mt-1 text-[#657080]">maximum rounds</p></div>
                <div><p className="metric-number text-2xl">100%</p><p className="mt-1 text-[#657080]">citations shown</p></div>
                <div><p className="metric-number text-2xl">0</p><p className="mt-1 text-[#657080]">trades or orders</p></div>
              </div>
            </div>
          </div>

          <div className="archive-panel p-6 sm:p-8">
            <form onSubmit={runResearch}>
              <div className="grid gap-5 sm:grid-cols-2">
                <TickerSelect value={ticker} onChange={setTicker} label="Public company" />
                <div className="space-y-2">
                  <label className="block text-sm font-bold text-[#17243a]" htmlFor="filing-type">Filing type</label>
                  <select id="filing-type" className="field" value={filingType} onChange={(event) => setFilingType(event.target.value)}>
                    <option value="10-K">10-K · Annual report</option>
                    <option value="10-Q">10-Q · Quarterly report</option>
                    <option value="8-K">8-K · Current report</option>
                  </select>
                </div>
              </div>

              <button className="btn-primary mt-6 w-full sm:w-auto" type="submit" disabled={running || !ticker.trim()}>
                {running ? "Research in progress" : `Analyze ${ticker || "company"}`}
                <span aria-hidden="true">→</span>
              </button>
            </form>

            <div className="mt-8 border-t rule pt-7">
              <p className="eyebrow text-[#657080]">Live research trace</p>
              <ol className="mt-5 grid gap-3 sm:grid-cols-2">
                {steps.map((step, index) => {
                  const current = phase === step.key || (step.key === "complete" && phase === "verifying");
                  const complete = phase === "complete" || (activeIndex > index && phase !== "error");
                  return (
                    <li className="border rule bg-[#fbf8f2] p-4" key={step.key}>
                      <div className="flex items-center gap-3">
                        <span className={`status-dot ${complete ? "complete" : current ? "active" : ""}`} />
                        <span className="text-xs font-bold uppercase tracking-[0.12em] text-[#657080]">Step {index + 1}</span>
                      </div>
                      <p className="mt-3 font-bold">{step.title}</p>
                      <p className="mt-1 text-sm leading-5 text-[#657080]">{step.copy}</p>
                    </li>
                  );
                })}
              </ol>
            </div>

            {error ? (
              <div className="mt-6 border border-[#b65d55]/35 bg-[#b65d55]/10 p-4 text-sm text-[#793a35]" role="alert">
                <p className="font-bold">This run stopped safely.</p>
                <p className="mt-1">{error}</p>
              </div>
            ) : null}

            {phase === "complete" && job?.reportId ? (
              <div className="mt-6 border border-[#17243a] bg-[#17243a] p-5 text-white">
                <div className="grid gap-5 sm:grid-cols-[1fr_auto] sm:items-end">
                  <div>
                    <p className="eyebrow text-[#e5c268]">Research complete</p>
                    <h3 className="display mt-2 text-3xl">The evidence trail is ready.</h3>
                    <p className="mt-3 text-sm leading-6 text-white/70">
                      {job.rounds ?? 1} agent round{job.rounds === 1 ? "" : "s"}. {supported ? `${supported.count} of ${supported.total} citations met the support threshold.` : "Citations verified."}
                    </p>
                  </div>
                  <div className="text-left sm:text-right">
                    <p className="metric-number text-4xl text-[#e5c268]">{citationScore === null ? "N/A" : `${Math.round(citationScore * 100)}%`}</p>
                    <p className="text-xs uppercase tracking-[0.12em] text-white/55">citation precision</p>
                  </div>
                </div>

                {job.trace && job.trace.length > 0 ? (
                  <div className="mt-5 flex flex-wrap gap-2 border-t border-white/15 pt-4">
                    {job.trace.map((trace) => (
                      <span className="border border-white/20 px-3 py-2 text-xs" key={`${trace.round}-${trace.strategy}`}>
                        Round {trace.round}: {trace.strategy} retrieval · {Math.round(trace.precision * 100)}%
                      </span>
                    ))}
                  </div>
                ) : null}

                <Link className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-[#e5c268] underline underline-offset-4" href={`/report/${job.reportId}`}>
                  Open the cited report <span aria-hidden="true">→</span>
                </Link>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section id="how-it-works" className="border-t rule bg-[#17243a] text-white">
        <div className="mx-auto grid max-w-7xl gap-12 px-5 py-16 lg:grid-cols-2 lg:px-8 lg:py-24">
          <div>
            <p className="eyebrow text-[#e5c268]">Why this is agentic</p>
            <h2 className="display mt-4 text-4xl leading-tight sm:text-5xl">The next move depends on what the filing supports.</h2>
          </div>
          <div className="space-y-6 text-base leading-7 text-white/75">
            <p>
              A single-pass summarizer always does the same thing. EDGAR Lens evaluates its own cited output and uses that result to decide whether to stop or retrieve a broader set of filing sections and try again.
            </p>
            <p>
              The flexible part is bounded. Citation scoring, the two-round limit, fallback behavior, and the final stop condition remain deterministic and inspectable.
            </p>
            <div className="border-l-2 border-[#e5c268] pl-5 text-white">
              <p className="font-bold">Generate → verify → adapt → keep the best supported result.</p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
