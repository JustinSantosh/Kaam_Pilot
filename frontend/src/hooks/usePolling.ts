"use client";

import { useEffect, useRef } from "react";

/** Run `fn` every `ms` while the tab is visible (D-016). Pass `enabled=false` to pause. */
export function usePolling(fn: () => void | Promise<void>, ms: number, enabled = true) {
  const saved = useRef(fn);
  useEffect(() => {
    saved.current = fn;
  }, [fn]);

  useEffect(() => {
    if (!enabled) return;
    let stopped = false;
    const tick = async () => {
      if (stopped || document.visibilityState !== "visible") return;
      try {
        await saved.current();
      } catch {
        /* the next tick retries; errors are shown by the caller */
      }
    };
    void tick();
    const id = window.setInterval(tick, ms);
    return () => {
      stopped = true;
      window.clearInterval(id);
    };
  }, [ms, enabled]);
}
