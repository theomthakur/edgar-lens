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
      <section>
        <div className="mx-auto grid max-w-6xl gap-10 px-5 py-16 lg:grid-cols-[1.2fr_0.8fr] lg:px-8 lg:py-20">
          <div>
            <p className="eyebrow text-[#2563eb]">Research public company filings</p>
            <h1 className="display mobile-hero-title mt-4 max-w-3xl text-[3rem] leading-[1.05] sm:text-[4rem] lg:text-[4.5rem]">
              Understand a filing with the evidence in view.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[#64748b]">
              EDGAR Lens turns SEC filings into a concise research brief and links every finding back to the source excerpt that supports it.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a className="btn-primary mobile-action" href="#research">Run a filing analysis <span aria-hidden="true">→</span></a>
              <Link className="btn-secondary mobile-action" href="/report/demo-report-001">Explore a sample report</Link>
            </div>
          </div>

          <div className="card self-end p-6 sm:p-7">
            <div className="flex items-center justify-between gap-4 border-b rule pb-4">
              <p className="text-sm font-semibold text-[#172033]">How a report is built</p>
              <span className="signal-tag">Source-backed</span>
            </div>
            <div className="mt-5 space-y-5">
              {[
                ["1", "Read the filing", "Retrieve the latest annual, quarterly, or current report from SEC EDGAR."],
                ["2", "Build the brief", "Pull together the sections most relevant to the company and filing type."],
                ["3", "Check support", "Evaluate each citation before the brief is presented."],
              ].map(([number, title, copy]) => (
                <div className="grid grid-cols-[1.6rem_1fr] gap-3" key={number}>
                  <span className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-[#eff6ff] text-xs font-semibold text-[#1d4ed8]">{number}</span>
                  <div>
                    <p className="text-sm font-semibold text-[#172033]">{title}</p>
                    <p className="mt-1 text-sm leading-5 text-[#64748b]">{copy}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="research" className="border-y rule bg-white">
        <div className="mx-auto grid max-w-6xl gap-10 px-5 py-14 lg:grid-cols-[0.8fr_1.2fr] lg:px-8 lg:py-16">
          <div>
            <p className="eyebrow text-[#2563eb]">New analysis</p>
            <h2 className="display mt-3 text-3xl leading-tight sm:text-4xl">Choose a company and filing.</h2>
            <p className="mt-4 max-w-lg leading-7 text-[#64748b]">
              This is research support, not investment advice. You will always see the supporting excerpts in the final report.
            </p>

            <div className="mt-7 grid grid-cols-3 gap-3 border-t rule pt-5 text-sm">
              <div><p className="metric-number text-xl text-[#172033]">2</p><p className="mt-1 text-[#64748b]">round limit</p></div>
              <div><p className="metric-number text-xl text-[#172033]">100%</p><p className="mt-1 text-[#64748b]">citations visible</p></div>
              <div><p className="metric-number text-xl text-[#172033]">0</p><p className="mt-1 text-[#64748b]">trading actions</p></div>
            </div>
          </div>

          <div className="card p-6 sm:p-7">
            <form onSubmit={runResearch}>
              <div className="grid gap-5 sm:grid-cols-2">
                <TickerSelect value={ticker} onChange={setTicker} label="Public company" />
                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-[#172033]" htmlFor="filing-type">Filing type</label>
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
              <p className="text-sm font-semibold text-[#172033]">Research progress</p>
              <ol className="mt-5 grid gap-3 sm:grid-cols-2">
                {steps.map((step, index) => {
                  const current = phase === step.key || (step.key === "complete" && phase === "verifying");
                  const complete = phase === "complete" || (activeIndex > index && phase !== "error");
                  return (
                    <li className="rounded-lg border rule bg-[#f8fafc] p-4" key={step.key}>
                      <div className="flex items-center gap-3">
                        <span className={`status-dot ${complete ? "complete" : current ? "active" : ""}`} />
                        <span className="text-xs font-medium text-[#64748b]">Step {index + 1}</span>
                      </div>
                      <p className="mt-3 text-sm font-semibold text-[#172033]">{step.title}</p>
                      <p className="mt-1 text-sm leading-5 text-[#64748b]">{step.copy}</p>
                    </li>
                  );
                })}
              </ol>
            </div>

            {error ? (
              <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
                <p className="font-bold">This run stopped safely.</p>
                <p className="mt-1">{error}</p>
              </div>
            ) : null}

            {phase === "complete" && job?.reportId ? (
              <div className="mt-6 rounded-lg border border-[#172033] bg-[#172033] p-5 text-white">
                <div className="grid gap-5 sm:grid-cols-[1fr_auto] sm:items-end">
                  <div>
                    <p className="text-sm font-medium text-blue-200">Research complete</p>
                    <h3 className="display mt-2 text-2xl">Your report is ready.</h3>
                    <p className="mt-3 text-sm leading-6 text-white/70">
                      {job.rounds ?? 1} agent round{job.rounds === 1 ? "" : "s"}. {supported ? `${supported.count} of ${supported.total} citations met the support threshold.` : "Citations verified."}
                    </p>
                  </div>
                  <div className="text-left sm:text-right">
                    <p className="metric-number text-3xl text-white">{citationScore === null ? "N/A" : `${Math.round(citationScore * 100)}%`}</p>
                    <p className="text-xs text-white/55">citation precision</p>
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

                <Link className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-blue-200 underline underline-offset-4" href={`/report/${job.reportId}`}>
                  Open the cited report <span aria-hidden="true">→</span>
                </Link>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section id="how-it-works" className="mx-auto max-w-6xl px-5 py-16 lg:px-8 lg:py-20">
        <div className="grid gap-10 border-t rule pt-10 lg:grid-cols-[0.8fr_1.2fr]">
          <div>
            <p className="eyebrow text-[#2563eb]">How it works</p>
            <h2 className="display mt-3 text-3xl leading-tight sm:text-4xl">The workflow can adapt, but it stays bounded.</h2>
          </div>
          <div className="space-y-5 text-base leading-7 text-[#64748b]">
            <p>
              A single-pass summarizer always does the same thing. EDGAR Lens evaluates its own cited output and uses that result to decide whether to stop or retrieve a broader set of filing sections and try again.
            </p>
            <p>
              The flexible part is bounded. Citation scoring, the two-round limit, fallback behavior, and the final stop condition remain deterministic and inspectable.
            </p>
            <div className="rounded-lg border border-[#dbeafe] bg-[#eff6ff] p-4 text-[#1e3a8a]">
              <p className="font-semibold">Generate, verify, adapt if needed, then keep the best supported result.</p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
