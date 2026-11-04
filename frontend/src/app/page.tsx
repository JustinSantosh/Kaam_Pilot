import Link from "next/link";

const roles = [
  {
    href: "/customer",
    eyebrow: "For customers",
    title: "Start a quotation",
    description:
      "Describe what you need in a familiar chat. Get clear follow-up questions and a quote to review.",
    action: "Open Customer Hub",
  },
  {
    href: "/business",
    eyebrow: "For business owners",
    title: "Review your inbox",
    description:
      "Check specifications, validate pricing, and approve or revise every quote before it is sent.",
    action: "Open Business Ops",
  },
];

export default function Home() {
  return (
    <div className="space-y-16 pb-10 pt-8 sm:pt-14">
      <section className="relative overflow-hidden rounded-3xl border border-brand-100 bg-white px-6 py-12 shadow-sm sm:px-12 sm:py-16">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-20 -top-32 h-96 w-96 rounded-full bg-brand-50"
        />
        <div className="relative max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-brand-600">
            Quoting, with people in control
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950 sm:text-6xl">
            From a customer&apos;s request to a quote they can trust.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
            KaamPilot helps trade businesses turn clear requirements into consistent quotations.
            The system organizes the details; your team checks the work and approves every quote.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/customer"
              className="rounded-lg bg-brand-700 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
            >
              Try the customer chat
            </Link>
            <Link
              href="/business"
              className="rounded-lg border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
            >
              Go to Business Ops
            </Link>
          </div>
        </div>
      </section>

      <section aria-labelledby="roles-heading">
        <div className="mb-5">
          <p className="text-sm font-semibold text-brand-700">One workflow, two roles</p>
          <h2 id="roles-heading" className="mt-1 text-2xl font-semibold text-slate-950">
            Where would you like to begin?
          </h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {roles.map((role) => (
            <article
              key={role.href}
              className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <p className="text-sm font-medium text-brand-700">{role.eyebrow}</p>
              <h3 className="mt-2 text-xl font-semibold text-slate-950">{role.title}</h3>
              <p className="mt-2 flex-1 leading-7 text-slate-600">{role.description}</p>
              <Link
                href={role.href}
                className="mt-6 w-fit font-semibold text-brand-700 underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-700"
              >
                {role.action} <span aria-hidden="true">→</span>
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section
        aria-label="KaamPilot workflow guarantees"
        className="grid gap-3 border-t border-slate-200 pt-6 sm:grid-cols-3"
      >
        {[
          ["01", "Details are extracted", "Requests become structured specifications."],
          ["02", "Pricing stays deterministic", "Catalog rules calculate every amount."],
          ["03", "Owners approve every quote", "Nothing is sent to a customer without review."],
        ].map(([number, title, description]) => (
          <div key={number} className="rounded-xl bg-brand-50/70 p-5">
            <p className="text-sm font-semibold text-brand-700">{number}</p>
            <h2 className="mt-2 font-semibold text-slate-950">{title}</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
