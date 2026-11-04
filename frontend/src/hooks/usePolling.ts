"use client";

import { useEffect, useRef } from "react";

/** Run `fn` sequentially while visible, backing off on errors (D-016). */
export function usePolling(
  fn: () => void | Promise<void>,
  ms: number,
  enabled: boolean,
  onError: (error: unknown) => void,
) {
  const saved = useRef(fn);
  const savedOnError = useRef(onError);
  useEffect(() => {
    saved.current = fn;
  }, [fn]);
  useEffect(() => {
    savedOnError.current = onError;
  }, [onError]);

  useEffect(() => {
    if (!enabled) return;
    let stopped = false;
    let running = false;
    let failures = 0;
    let timer: number | undefined;
    const clearTimer = () => {
      if (timer !== undefined) window.clearTimeout(timer);
      timer = undefined;
    };
    const schedule = (delay: number) => {
      clearTimer();
      if (!stopped && document.visibilityState === "visible") {
        timer = window.setTimeout(() => void tick(), delay);
      }
    };
    const tick = async () => {
      if (stopped || running || document.visibilityState !== "visible") return;
      running = true;
      try {
        await saved.current();
        failures = 0;
      } catch (error) {
        failures += 1;
        savedOnError.current(error);
      } finally {
        running = false;
        schedule(Math.min(ms * 2 ** Math.min(failures, 4), 60_000));
      }
    };
    const onVisibilityChange = () => {
      if (document.visibilityState === "hidden") clearTimer();
      else if (!running) schedule(0);
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    schedule(0);
    return () => {
      stopped = true;
      clearTimer();
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [ms, enabled]);
}
