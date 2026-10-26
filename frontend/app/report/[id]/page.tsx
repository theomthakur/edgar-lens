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
    <article className="mx-auto max-w-6xl px-5 py-12 lg:px-8 lg:py-16">
      <Link className="text-sm font-semibold text-[#2563eb] hover:underline" href="/#research">
        ← Run another analysis
      </Link>

      <header className="mt-8 grid gap-8 border-b rule pb-10 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <p className="eyebrow text-[#2563eb]">Citation-backed filing research</p>
          <h1 className="display mt-3 text-4xl sm:text-5xl">{report.ticker} research brief</h1>
          <p className="mt-5 max-w-3xl text-lg leading-8 text-[#64748b]">{report.summary}</p>
        </div>
        <div className="grid gap-4 lg:border-l lg:pl-6">
          <div>
            <p className="text-xs font-medium text-[#64748b]">Report reference</p>
            <p className="mt-2 max-w-[16rem] break-all font-mono text-xs text-[#172033]">{report.reportId}</p>
          </div>
          <a className="inline-flex w-fit items-center gap-2 rounded-lg border border-[#cbd5e1] bg-white px-4 py-3 text-sm font-semibold text-[#172033] transition hover:border-[#94a3b8] hover:bg-[#f8fafc]" href={getReportPdfUrl(report.reportId)}>
            Download PDF <span aria-hidden="true">↓</span>
          </a>
        </div>
      </header>

      <div className="mt-12 grid gap-10 lg:grid-cols-[0.72fr_1.28fr]">
        <aside>
          <p className="eyebrow text-[#64748b]">Key findings</p>
          <p className="display mt-3 text-3xl">Key findings</p>
        </aside>
        <section className="card divide-y rule" aria-labelledby="findings-title">
          <h2 id="findings-title" className="sr-only">Key findings</h2>
          {report.keyFindings.map((finding, index) => (
            <div className="grid grid-cols-[2.5rem_1fr] gap-4 p-5 sm:p-6" key={finding}>
              <span className="metric-number text-xl text-[#2563eb]">0{index + 1}</span>
              <p className="leading-7 text-[#334155]">{finding}</p>
            </div>
          ))}
        </section>
      </div>

      <section className="mt-16 border-t rule pt-10">
        <div className="grid gap-8 lg:grid-cols-[0.72fr_1.28fr]">
          <div>
            <p className="eyebrow text-[#64748b]">Source trail</p>
            <h2 className="display mt-3 text-3xl">Evidence used in this report</h2>
            <p className="mt-4 max-w-sm text-sm leading-6 text-[#64748b]">
              These excerpts are shown so a reviewer can inspect the source rather than trust the generated summary.
            </p>
          </div>
          <ol className="space-y-4">
            {report.citations.map((citation, index) => (
              <li className="card p-5 sm:p-6" key={`${citation.sourceTitle}-${citation.section}-${index}`}>
                <div className="flex flex-wrap items-center justify-between gap-3 border-b rule pb-4">
                  <p className="text-sm font-semibold text-[#172033]">{citation.sourceTitle}</p>
                  <span className="rounded-full border border-[#e2e8f0] bg-[#f8fafc] px-2.5 py-1 text-xs font-medium text-[#64748b]">
                    Source {index + 1}
                  </span>
                </div>
                <p className="mt-4 text-xs font-medium text-[#2563eb]">{citation.section}</p>
                <blockquote className="mt-3 border-l-2 border-[#93c5fd] pl-4 text-base leading-7 text-[#334155]">
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
