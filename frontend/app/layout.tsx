import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { BRAND_DESCRIPTION, BRAND_NAME } from "@/lib/brand";

export const metadata: Metadata = {
  title: { default: BRAND_NAME, template: `%s | ${BRAND_NAME}` },
  description: BRAND_DESCRIPTION,
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="sticky top-0 z-50 border-b rule bg-[#f7f3eb]/95 backdrop-blur-md">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 lg:px-8">
            <Link href="/" className="flex items-center gap-3" aria-label="EDGAR Lens home">
              <img className="brand-mark" src="/edgar-lens-mark.svg" alt="" aria-hidden="true" />
              <span>
                <strong className="block text-[0.9rem] leading-tight tracking-[-0.02em]">EDGAR Lens</strong>
                <span className="hidden text-[0.68rem] font-medium uppercase tracking-[0.15em] text-[#657080] sm:block">
                  A public filing reading room
                </span>
              </span>
            </Link>

            <nav className="flex items-center gap-5 text-sm sm:gap-8" aria-label="Primary navigation">
              <Link className="nav-link hidden sm:block" href="/#how-it-works">How it works</Link>
              <Link className="nav-link hidden sm:block" href="/report/demo-report-001">Sample report</Link>
              <Link className="btn-primary !min-h-0 !px-3 !py-2 sm:!px-4" href="/#research">
                <span className="sm:hidden">Research</span>
                <span className="hidden sm:inline">Run research</span>
              </Link>
            </nav>
          </div>
        </header>

        <main>{children}</main>

        <footer className="border-t rule bg-[#ece7dc]">
          <div className="mx-auto grid max-w-6xl gap-6 px-5 py-8 text-xs text-[#657080] sm:grid-cols-2 lg:px-8">
            <div>
              <div className="flex items-center gap-2">
                <img className="h-5 w-5" src="/edgar-lens-mark.svg" alt="" aria-hidden="true" />
                <p className="font-bold text-[#17243a]">EDGAR Lens</p>
              </div>
              <p className="mt-1 max-w-md">A bounded research agent for public SEC filings.</p>
            </div>
            <div className="sm:text-right">
              <p>Research support only. Not investment advice.</p>
              <p className="mt-1">Every generated claim should be checked against its cited source.</p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
