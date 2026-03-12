import { getReport } from "@/lib/api";
import CitationEvalPanel from "@/components/CitationEvalPanel";
import type { Metadata } from "next";
import { BRAND_NAME } from "@/lib/brand";

type Props = {
  params: Promise<{ id: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  return {
    title: `Report ${id} | ${BRAND_NAME}`,
  };
}

export default async function ReportPage({ params }: Props) {
  const { id } = await params;
  const report = await getReport(id);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Report for {report.ticker}</h1>
        <p className="text-sm text-slate-600">Report ID: {report.reportId}</p>
      </header>

      <section className="card p-6 space-y-3">
        <h2 className="text-lg font-medium">Summary</h2>
        <p>{report.summary}</p>
      </section>

      <section className="card p-6 space-y-3">
        <h2 className="text-lg font-medium">Key Findings</h2>
        <ul className="list-disc pl-6 text-sm text-slate-700">
          {report.keyFindings.map((finding) => (
            <li key={finding}>{finding}</li>
          ))}
        </ul>
      </section>

      <section className="card p-6 space-y-3">
        <h2 className="text-lg font-medium">Citations</h2>
        <ul className="space-y-3">
          {report.citations.map((citation) => (
            <li key={`${citation.sourceTitle}-${citation.section}`} className="rounded border p-3">
              <p className="font-medium">{citation.sourceTitle}</p>
              <p className="text-xs text-slate-500">Section: {citation.section}</p>
              <p className="mt-1 text-sm">{citation.excerpt}</p>
            </li>
          ))}
        </ul>
      </section>

      <CitationEvalPanel reportId={report.reportId} />
    </div>
  );
}
