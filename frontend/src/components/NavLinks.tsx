"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChatIcon, InboxIcon } from "./icons";

const LINKS = [
  { href: "/customer", label: "Customer Hub", Icon: ChatIcon },
  { href: "/business", label: "Business Ops", Icon: InboxIcon },
];

export function NavLinks() {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="flex gap-1 rounded-2xl border-2 border-ink bg-mist p-1">
      {LINKS.map(({ href, label, Icon }) => {
        const active = pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={`inline-flex min-h-11 items-center gap-2 rounded-xl px-3 text-[15px] font-extrabold sm:px-4 ${
              active ? "bg-ink text-white" : "text-ink hover:bg-white"
            }`}
          >
            <Icon size={18} />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
