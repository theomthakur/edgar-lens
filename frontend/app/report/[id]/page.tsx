import Link from "next/link";
import type { Metadata } from "next";
import { getReport, getReportPdfUrl } from "@/lib/api";
import CitationEvalPanel from "@/components/CitationEvalPanel";
import { BRAND_NAME } from "@/lib/brand";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  return { title: `Report ${id} | ${BRAND_NAME}` };
}

export default async function ReportPage({ params }: Props) {
  const { id } = await params;
  const report = await getReport(id);

  return (
    <article className="mx-auto max-w-7xl px-5 py-12 lg:px-8 lg:py-20">
      <Link className="text-sm font-bold text-[#355f9e] underline underline-offset-4" href="/#research">
        ← Run another analysis
      </Link>

      <header className="mt-8 grid gap-8 border-y rule py-10 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <p className="eyebrow text-[#355f9e]">Citation-backed filing research</p>
          <h1 className="display mt-3 text-5xl sm:text-6xl">{report.ticker} research brief</h1>
          <p className="mt-5 max-w-3xl text-lg leading-8 text-[#657080]">{report.summary}</p>
        </div>
        <div className="grid gap-4 border-l rule pl-6">
          <div>
            <p className="eyebrow text-[#657080]">Report reference</p>
            <p className="mt-2 max-w-[16rem] break-all font-mono text-xs text-[#17243a]">{report.reportId}</p>
          </div>
          <a className="inline-flex w-fit items-center gap-2 border border-[#17243a] bg-[#fffdfa] px-4 py-3 text-sm font-bold text-[#17243a] transition hover:bg-[#17243a] hover:text-white" href={getReportPdfUrl(report.reportId)}>
            Download PDF <span aria-hidden="true">↓</span>
          </a>
        </div>
      </header>

      <div className="mt-12 grid gap-10 lg:grid-cols-[0.72fr_1.28fr]">
        <aside>
          <p className="eyebrow text-[#657080]">What matters</p>
          <p className="display mt-3 text-3xl">Key findings</p>
        </aside>
        <section className="archive-panel divide-y rule" aria-labelledby="findings-title">
          <h2 id="findings-title" className="sr-only">Key findings</h2>
          {report.keyFindings.map((finding, index) => (
            <div className="grid grid-cols-[2.5rem_1fr] gap-4 p-5 sm:p-6" key={finding}>
              <span className="metric-number text-xl text-[#a64b3c]">0{index + 1}</span>
              <p className="leading-7">{finding}</p>
            </div>
          ))}
        </section>
      </div>

      <section className="mt-16 border-t rule pt-10">
        <div className="grid gap-8 lg:grid-cols-[0.72fr_1.28fr]">
          <div>
            <p className="eyebrow text-[#657080]">Source trail</p>
            <h2 className="display mt-3 text-3xl">Evidence used in this report</h2>
            <p className="mt-4 max-w-sm text-sm leading-6 text-[#657080]">
              These excerpts are shown so a reviewer can inspect the source rather than trust the generated summary.
            </p>
          </div>
          <ol className="space-y-4">
            {report.citations.map((citation, index) => (
              <li className="archive-panel ledger-card p-5 sm:p-6" key={`${citation.sourceTitle}-${citation.section}-${index}`}>
                <div className="flex flex-wrap items-center justify-between gap-3 border-b rule pb-4">
                  <p className="font-bold">{citation.sourceTitle}</p>
                  <span className="border rule bg-[#f7f3eb] px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-[0.12em] text-[#657080]">
                    Source {index + 1}
                  </span>
                </div>
                <p className="mt-4 text-xs font-bold uppercase tracking-[0.12em] text-[#355f9e]">{citation.section}</p>
                <blockquote className="mt-3 border-l-2 border-[#c79d43] pl-4 font-serif text-lg leading-8 text-[#17243a]">
                  “{citation.excerpt}”
                </blockquote>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <div className="mt-16">
        <CitationEvalPanel reportId={report.reportId} />
      </div>
    </article>
  );
}
