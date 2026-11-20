import type { Metadata } from "next";
import { Bricolage_Grotesque, Figtree } from "next/font/google";
import Link from "next/link";
import { LogoMark, Wordmark } from "@/components/Logo";
import { NavLinks } from "@/components/NavLinks";
import "./globals.css";

// Brand type (D-027): Bricolage Grotesque for headlines and big numbers, Figtree for everything else.
const display = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-bricolage",
  axes: ["opsz"],
});
const text = Figtree({ subsets: ["latin"], variable: "--font-figtree" });

export const metadata: Metadata = {
  title: "KaamPilot",
  description: "Message in. Quote out. You approve. Quotations for trade businesses.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${display.variable} ${text.variable}`}>
      <body className="bg-mist font-sans text-ink antialiased">
        <header className="sticky top-0 z-20 border-b-2 border-ink bg-white">
          <div className="mx-auto flex max-w-[1440px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5 sm:px-8">
            <Link href="/" aria-label="KaamPilot home" className="flex items-center gap-2.5 rounded-xl">
              <LogoMark size={36} />
              <Wordmark className="text-[26px]" />
            </Link>
            <NavLinks />
            <p className="ml-auto hidden text-sm font-bold text-ink-500 lg:block">
              AI padhta hai · Code ginta hai · Aap approve karte hain
            </p>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
