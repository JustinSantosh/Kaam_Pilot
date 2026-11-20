import Link from "next/link";
import type { ReactNode } from "react";
import { LogoMark, Wordmark } from "@/components/Logo";
import { ArrowRightIcon } from "@/components/icons";
import { StatusBadge } from "@/components/ui";

const CONTAINER = "mx-auto w-full max-w-[1440px] px-4 sm:px-8";
const PRESSABLE =
  "transition-[transform,box-shadow,background-color] active:translate-x-1 active:translate-y-1 active:shadow-none";
const PRIMARY = `inline-flex min-h-13 items-center gap-2.5 rounded-2xl border-2 border-ink bg-rani px-6 text-[17px] font-extrabold text-white shadow-pop hover:bg-rani-700 ${PRESSABLE}`;
const SECONDARY = `inline-flex min-h-13 items-center gap-2.5 rounded-2xl border-2 border-ink bg-white px-6 text-[17px] font-extrabold text-ink shadow-pop hover:bg-mist ${PRESSABLE}`;
const EYEBROW = "text-[13px] font-extrabold uppercase tracking-[0.12em] text-rani";
const H2 = "font-display text-[clamp(2.25rem,4.4vw,3.75rem)] font-extrabold leading-none tracking-[-0.04em] text-balance";

// An illustration only: the numbers are what the seed catalogue gives for this order.
const EXAMPLE_LINES = [
  ["40 black tees, embroidery + setup", "₹11,700.00"],
  ["20 white tees, embroidery + setup", "₹5,700.00"],
  ["CGST + SGST at 5%", "₹870.00"],
];
const WAVE = [8, 14, 20, 12, 24, 16, 10, 22, 26, 14, 9, 18, 24, 12, 8, 16, 22, 10, 14, 20, 12, 8];

const STEPS: {
  badge: string;
  hinglish: string;
  hinglishClass: string;
  title: string;
  body: string;
  visual: ReactNode;
}[] = [
  {
    badge: "bg-peacock-pop",
    hinglish: "AI padhta hai",
    hinglishClass: "text-peacock-700",
    title: "Reads the message",
    body: "Pulls out products, quantities, sizes and print type, even from “kaali tee, kadhai wala”. If something is missing, it asks for exactly that.",
    visual: (
      <span className="flex flex-wrap gap-2">
        {["black tee × 40", "white tee × 20", "embroidery", "front"].map((chip) => (
          <span
            key={chip}
            className="inline-flex min-h-7.5 items-center rounded-full bg-peacock-soft px-3 text-[13px] font-extrabold text-peacock-700"
          >
            {chip}
          </span>
        ))}
        <span className="inline-flex min-h-7.5 items-center rounded-full bg-marigold-soft px-3 text-[13px] font-extrabold">
          sizes? asked
        </span>
      </span>
    ),
  },
  {
    badge: "bg-marigold",
    hinglish: "Code ginta hai",
    hinglishClass: "text-ink",
    title: "Prices it exactly",
    body: "Your catalogue rates, bulk tiers and setup fees, plus the right GST: CGST and SGST in your state, IGST across states. The AI never touches a price.",
    visual: (
      <span className="flex flex-col gap-1.5 rounded-2xl border-2 border-dashed border-ink bg-white px-3.5 py-3 text-sm tabular-nums">
        <span className="flex justify-between gap-2.5">
          <span>40 × ₹280.00 + ₹500.00 setup</span>
          <b>₹11,700.00</b>
        </span>
        <span className="flex justify-between gap-2.5">
          <span>20 × ₹260.00 + ₹500.00 setup</span>
          <b>₹5,700.00</b>
        </span>
        <span className="flex justify-between gap-2.5">
          <span>CGST 2.5% + SGST 2.5%</span>
          <b>₹870.00</b>
        </span>
      </span>
    ),
  },
  {
    badge: "bg-rani-pop",
    hinglish: "Aap approve karte hain",
    hinglishClass: "text-rani",
    title: "You approve",
    body: "See what the customer said next to what the AI understood. Change a quantity or add a discount and it's re-priced as a new revision. Then send it.",
    visual: (
      <span className="flex flex-wrap gap-2.5">
        <span className="inline-flex min-h-11 items-center rounded-[14px] border-2 border-ink bg-white px-4 text-[15px] font-extrabold shadow-pop-sm">
          Edit
        </span>
        <span className="inline-flex min-h-11 items-center rounded-[14px] border-2 border-ink bg-rani px-4 text-[15px] font-extrabold text-white shadow-pop-sm">
          Approve &amp; send
        </span>
      </span>
    ),
  },
];

const PROMISES = [
  {
    title: "No AI prices. Ever.",
    color: "text-marigold",
    body: "The AI fills a form that has no price fields. Rates, discounts and tax come from your catalogue and the code.",
  },
  {
    title: "Every rupee shown.",
    color: "text-rani-pop",
    body: "Rates, setup fees, discount, taxable value and the CGST, SGST or IGST split, all in front of you before you send.",
  },
  {
    title: "Nothing sent without you.",
    color: "text-peacock-pop",
    body: "Quotes wait in your inbox until you approve, edit or reject them. Tricks hidden in a message don't change that.",
  },
];

function ExampleQuote() {
  return (
    <div
      role="img"
      aria-label="Example: a Hinglish message and a voice note become a priced quote of ₹18,270.00 that waits for the owner's OK"
      className="flex min-w-0 flex-col gap-3.5"
    >
      <div className="max-w-[400px] -rotate-2 self-start rounded-3xl rounded-bl-lg border-2 border-ink bg-white px-4.5 py-3.5 shadow-pop">
        <p className="text-[13px] font-extrabold text-ink-500">Ravi Kumar · Raipur</p>
        <p className="mt-1.5 text-[17px] font-semibold leading-snug">
          bhaiya 40 kaali tee aur 20 safed, front pe logo kadhai wala
        </p>
      </div>
      <div className="ml-6 max-w-[370px] rotate-1 self-start rounded-3xl rounded-bl-lg border-2 border-ink bg-white px-4 py-3 shadow-pop sm:ml-12">
        <div className="flex items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full border-2 border-ink bg-peacock-pop">
            <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M7 4.5v15l12.5-7.5Z" fill="currentColor" />
            </svg>
          </span>
          <span className="flex h-7 flex-1 items-center gap-[3px] overflow-hidden">
            {WAVE.map((height, i) => (
              <span key={i} className="w-[3px] shrink-0 rounded-sm bg-ink" style={{ height }} />
            ))}
          </span>
          <span className="text-[13px] font-extrabold tabular-nums text-ink-700">0:09</span>
        </div>
        <p className="mt-2 text-sm leading-snug text-ink-700">
          <b className="text-peacock-700">Transcribed:</b> sizes: kaali wali M 20 L 20, safed wali M 10 L 10
        </p>
      </div>
      <svg width="200" height="56" viewBox="0 0 200 56" aria-hidden="true" className="self-center overflow-visible">
        <path
          d="M8 6C60 6 60 50 110 46S170 20 186 40"
          fill="none"
          stroke="#1E1240"
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeDasharray="1 8"
        />
        <path d="M191 48 189.2 38.1 182 43.5Z" fill="#1E1240" stroke="#1E1240" strokeWidth="2" strokeLinejoin="round" />
      </svg>
      <span className="relative z-10 -mb-8 mr-4 inline-flex min-h-11 rotate-[5deg] items-center self-end rounded-full border-2 border-ink bg-leaf-pop px-4.5 font-display text-[19px] font-extrabold shadow-pop-sm">
        GST sahi hai
      </span>
      <div className="w-full max-w-[440px] rotate-[1.5deg] self-end overflow-hidden rounded-3xl border-2 border-ink bg-white shadow-pop-lg">
        <div className="flex items-center gap-2.5 bg-ink px-4.5 py-3.5 text-white">
          <span className="font-display text-lg font-extrabold">KP-2026-0003</span>
          <span className="text-[13px] font-bold text-[#C9C0E0]">Rev 1</span>
        </div>
        <dl className="flex flex-col gap-2 px-4.5 pb-1.5 pt-4 text-[15px] tabular-nums">
          {EXAMPLE_LINES.map(([label, amount]) => (
            <div key={label} className="flex justify-between gap-3">
              <dt className="text-ink-700">{label}</dt>
              <dd className="font-bold">{amount}</dd>
            </div>
          ))}
        </dl>
        <div className="mx-4.5 mt-2 flex flex-wrap items-center justify-between gap-3 border-t-2 border-dashed border-ink pb-4 pt-3">
          <StatusBadge status="awaiting_approval" />
          <span className="font-display text-[32px] font-extrabold tracking-[-0.03em] tabular-nums">₹18,270.00</span>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <main className="bg-white">
      <section className={`${CONTAINER} pb-4 pt-6 sm:pt-8`}>
        <div className="grid items-center gap-12 rounded-[36px] border-2 border-ink bg-marigold bg-dots p-6 shadow-pop-lg sm:p-10 lg:grid-cols-[1.05fr_1fr] lg:p-16">
          <div className="flex min-w-0 flex-col items-start gap-6">
            <p className="inline-flex min-h-9 items-center rounded-full border-2 border-ink bg-white px-4 text-[15px] font-extrabold">
              Quotes for trade businesses
            </p>
            <h1 className="font-display text-[clamp(3rem,6.4vw,5.75rem)] font-extrabold leading-[0.96] tracking-[-0.045em] text-balance">
              Message in. Quote out.{" "}
              <span className="mt-[0.12em] inline-block -rotate-2 rounded-[20px] border-2 border-ink bg-rani-pop px-[0.18em] pb-[0.06em] shadow-[5px_5px_0_var(--color-ink)]">
                You approve.
              </span>
            </h1>
            <p className="max-w-[560px] text-xl leading-relaxed text-pretty">
              Customers send Hinglish texts and voice notes. KaamPilot turns them into a priced quote with the
              right GST, and nothing goes out until you say yes.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/customer" className={PRIMARY}>
                Try the customer chat
                <ArrowRightIcon size={20} strokeWidth={2.2} />
              </Link>
              <Link href="/business" className={SECONDARY}>
                Open Business Ops
              </Link>
            </div>
          </div>
          <ExampleQuote />
        </div>
      </section>

      <section id="how" aria-labelledby="how-title" className={`${CONTAINER} py-20 sm:py-24`}>
        <p className={EYEBROW}>How it flies</p>
        <h2 id="how-title" className={`${H2} mt-3.5 max-w-3xl`}>
          Three steps. The last one is yours.
        </h2>
        <ol className="mt-12 grid gap-6 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.title} className="flex flex-col gap-4 rounded-[28px] border-2 border-ink bg-mist p-7">
              <span className="flex items-center gap-3">
                <span
                  className={`flex size-12 items-center justify-center rounded-full border-2 border-ink font-display text-xl font-extrabold ${step.badge}`}
                >
                  {i + 1}
                </span>
                <span className={`font-display text-xl font-extrabold ${step.hinglishClass}`}>{step.hinglish}</span>
              </span>
              <h3 className="font-display text-[30px] font-extrabold leading-[1.05] tracking-[-0.03em]">
                {step.title}
              </h3>
              <p className="text-[17px] leading-relaxed text-ink-700 text-pretty">{step.body}</p>
              <span aria-hidden="true" className="mt-auto">
                {step.visual}
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="roles-title" className={`${CONTAINER} pb-24`}>
        <p className={EYEBROW}>One flow, two sides</p>
        <h2 id="roles-title" className={`${H2} mt-3.5`}>
          Where do you want to start?
        </h2>
        <div className="mt-10 grid gap-6 lg:grid-cols-2">
          <article className="flex flex-col items-start gap-4 rounded-[32px] border-2 border-ink bg-rani-pop p-7 shadow-pop-lg sm:p-11">
            <p className="text-sm font-extrabold uppercase tracking-[0.1em]">For customers</p>
            <h3 className="font-display text-[44px] font-extrabold leading-none tracking-[-0.04em]">Customer Hub</h3>
            <p className="max-w-[520px] text-lg leading-relaxed text-pretty">
              Chat the way you already do. Type it or send a voice note, answer a quick question if something&apos;s
              missing, and get the quote as a PDF right in the chat.
            </p>
            <Link
              href="/customer"
              className={`mt-2 inline-flex min-h-12 items-center gap-2.5 rounded-[14px] border-2 border-ink bg-white px-5 font-extrabold shadow-pop-sm hover:bg-mist ${PRESSABLE}`}
            >
              Open Customer Hub
              <ArrowRightIcon size={20} strokeWidth={2.2} />
            </Link>
          </article>
          <article className="flex flex-col items-start gap-4 rounded-[32px] border-2 border-ink bg-ink p-7 text-white shadow-[6px_6px_0_var(--color-marigold)] sm:p-11">
            <p className="text-sm font-extrabold uppercase tracking-[0.1em] text-marigold">For owners</p>
            <h3 className="font-display text-[44px] font-extrabold leading-none tracking-[-0.04em]">Business Ops</h3>
            <p className="max-w-[520px] text-lg leading-relaxed text-[#E3DDF2] text-pretty">
              One inbox for every quote. See what the customer said, what the AI understood and how the code priced
              it, then approve, edit or reject.
            </p>
            <Link
              href="/business"
              className={`mt-2 inline-flex min-h-12 items-center gap-2.5 rounded-[14px] border-2 border-marigold bg-marigold px-5 font-extrabold text-ink shadow-[3px_3px_0_var(--color-rani-pop)] ${PRESSABLE}`}
            >
              Open Business Ops
              <ArrowRightIcon size={20} strokeWidth={2.2} />
            </Link>
          </article>
        </div>
      </section>

      <section aria-label="What KaamPilot promises" className="border-y-2 border-ink bg-ink text-white">
        <div className={`${CONTAINER} grid gap-10 py-20 md:grid-cols-3`}>
          {PROMISES.map((promise) => (
            <div key={promise.title} className="flex flex-col gap-3.5">
              <h2
                className={`font-display text-[40px] font-extrabold leading-[1.02] tracking-[-0.035em] ${promise.color}`}
              >
                {promise.title}
              </h2>
              <p className="text-[17px] leading-relaxed text-[#C9C0E0]">{promise.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className={`${CONTAINER} py-20`}>
        <div className="flex flex-col items-center gap-5 rounded-[36px] border-2 border-ink bg-mist px-5 py-10 text-center sm:px-12 sm:py-16">
          <h2 className="font-display text-[clamp(2.5rem,5vw,4.25rem)] font-extrabold leading-none tracking-[-0.045em] text-balance">
            Got a customer waiting?
          </h2>
          <p className="max-w-[560px] text-[19px] leading-relaxed text-ink-700">
            Open the chat, pick a demo scenario, and watch the quote land in Business Ops.
          </p>
          <Link href="/customer" className={PRIMARY}>
            Try the customer chat
            <ArrowRightIcon size={20} strokeWidth={2.2} />
          </Link>
        </div>
      </section>

      <footer className="border-t-2 border-ink bg-white">
        <div className={`${CONTAINER} flex flex-wrap items-center justify-between gap-x-8 gap-y-4 py-7`}>
          <span className="flex items-center gap-2.5">
            <LogoMark size={32} />
            <Wordmark className="text-2xl" />
          </span>
          <p className="text-sm font-bold text-ink-500">AI padhta hai · Code ginta hai · Aap approve karte hain</p>
          <nav aria-label="Footer" className="flex gap-1">
            <Link href="/customer" className="inline-flex min-h-11 items-center px-3 text-[15px] font-bold hover:text-rani">
              Customer Hub
            </Link>
            <Link href="/business" className="inline-flex min-h-11 items-center px-3 text-[15px] font-bold hover:text-rani">
              Business Ops
            </Link>
          </nav>
        </div>
      </footer>
    </main>
  );
}
