import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { NavLinks } from "@/components/NavLinks";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "KaamPilot",
  description: "Human-in-the-loop quotations for trade businesses",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
            <span className="text-lg font-semibold text-brand-700">
              Kaam<span className="text-brand-500">Pilot</span>
            </span>
            <NavLinks />
            <span className="ml-auto hidden text-xs text-slate-500 sm:block">
              The LLM reads · Code calculates · The owner approves
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
