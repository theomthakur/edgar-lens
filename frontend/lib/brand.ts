export const BRAND_NAME = "EDGAR Lens";
export const BRAND_TAGLINE = "Agentic Finance Research Workspace";
export const BRAND_DESCRIPTION =
  "Ingest SEC filings, generate citation-backed insights, and evaluate research quality.";

export function pageTitle(title: string): string {
  return `${title} | ${BRAND_NAME}`;
}
