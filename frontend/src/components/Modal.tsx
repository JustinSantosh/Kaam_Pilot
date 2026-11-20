"use client";

import { useEffect, type ReactNode } from "react";
import { CloseIcon } from "./icons";

export function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/55 p-4"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`flex max-h-[90vh] w-full flex-col overflow-hidden rounded-[28px] border-2 border-ink bg-white shadow-pop-lg ${
          wide ? "max-w-5xl" : "max-w-lg"
        }`}
      >
        <div className="flex items-center justify-between gap-4 border-b-2 border-ink bg-marigold bg-dots px-5 py-3.5">
          <h3 className="font-display text-xl font-extrabold leading-tight tracking-[-0.02em]">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex size-11 shrink-0 items-center justify-center rounded-[14px] border-2 border-ink bg-white hover:bg-mist"
          >
            <CloseIcon size={20} strokeWidth={2.4} />
          </button>
        </div>
        <div className="overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  );
}
