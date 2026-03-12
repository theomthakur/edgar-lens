import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { BRAND_DESCRIPTION, BRAND_NAME, BRAND_TAGLINE } from "@/lib/brand";

export const metadata: Metadata = {
  title: {
    default: BRAND_NAME,
    template: `%s | ${BRAND_NAME}`,
  },
  description: BRAND_DESCRIPTION,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const disclaimer =
    process.env.NEXT_PUBLIC_APP_DISCLAIMER ||
    "For educational research only. Not investment advice.";

  return (
    <html lang="en">
      <body>
        <header className="border-b border-slate-200 bg-white/75 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
            <Link href="/" className="flex items-center gap-3">
              <span className="brand-badge">EL</span>
              <span>
                <strong className="block text-sm leading-tight">{BRAND_NAME}</strong>
                <span className="text-xs text-slate-600">{BRAND_TAGLINE}</span>
              </span>
            </Link>

            <nav className="flex items-center gap-2 text-sm">
              <Link className="nav-link" href="/">
                Ingest
              </Link>
              <Link className="nav-link" href="/analyze">
                Analyze
              </Link>
              <Link className="nav-link" href="/compare">
                Compare
              </Link>
            </nav>
          </div>
        </header>

        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="mx-auto mt-6 max-w-6xl px-4 pb-8 text-xs text-slate-600">
          <div className="rounded border border-slate-200 bg-white/80 p-3">
            <strong>Disclaimer:</strong> {disclaimer}
          </div>
        </footer>
      </body>
    </html>
  );
}
