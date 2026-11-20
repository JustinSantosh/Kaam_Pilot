"use client";

import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { LogoutIcon, RefreshIcon } from "@/components/icons";
import { InboxTable, type InboxFilter } from "@/components/InboxTable";
import { LogoMark } from "@/components/Logo";
import { QuoteInspector } from "@/components/QuoteInspector";
import { Button, Card, ErrorNote } from "@/components/ui";
import { usePolling } from "@/hooks/usePolling";
import {
  api,
  ApiError,
  type CatalogOption,
  type Decision,
  type QuoteDetail,
  type QuoteSummary,
} from "@/lib/api";

const PAGE = "mx-auto max-w-[1440px] px-4 sm:px-8";

export default function BusinessOps() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [filter, setFilter] = useState<InboxFilter>("awaiting_approval");
  const [quotes, setQuotes] = useState<QuoteSummary[]>([]);
  const [inboxLoaded, setInboxLoaded] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<QuoteDetail | null>(null);
  const [catalog, setCatalog] = useState<CatalogOption[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inboxError, setInboxError] = useState<string | null>(null);
  const [totalBeforeEdit, setTotalBeforeEdit] = useState<number | null>(null);

  useEffect(() => {
    api.authSession().then(() => setAuthenticated(true)).catch(() => setAuthenticated(false));
  }, []);

  useEffect(() => {
    if (!authenticated) return;
    api.catalog().then(setCatalog).catch((e) => {
      setError(e instanceof ApiError ? e.message : "Could not load the product catalog.");
    });
  }, [authenticated]);

  const refreshInbox = useCallback(async () => {
    setQuotes(await api.inbox(filter));
    setInboxLoaded(true);
    setInboxError(null);
  }, [filter]);

  const refreshDetail = useCallback(async () => {
    if (selectedId) setDetail(await api.quote(selectedId));
  }, [selectedId]);
  const reportInboxError = useCallback((e: unknown) => {
    setInboxError(
      e instanceof ApiError ? `${e.message} (${e.code})` : "Could not refresh the inbox.",
    );
  }, []);
  const reportDetailError = useCallback((e: unknown) => {
    setError(e instanceof ApiError ? `${e.message} (${e.code})` : "Could not refresh this quote.");
  }, []);

  usePolling(refreshInbox, 3000, authenticated === true, reportInboxError);
  usePolling(
    refreshDetail,
    5000,
    authenticated === true && Boolean(selectedId),
    reportDetailError,
  );

  const signIn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthError(null);
    try {
      await api.login(password);
      setPassword("");
      setAuthenticated(true);
    } catch (e) {
      setAuthError(e instanceof ApiError ? e.message : "Could not sign in.");
    }
  };

  const signOut = async () => {
    await api.logout();
    setAuthenticated(false);
    setSelectedId(null);
    setDetail(null);
  };

  const select = (id: string) => {
    setSelectedId(id);
    setDetail(null);
    setError(null);
    setTotalBeforeEdit(null);
  };

  const decide = async (decision: Decision): Promise<boolean> => {
    if (!detail) return false;
    setBusy(true);
    setError(null);
    try {
      const before = detail.total_paise;
      const updated = await api.decide(detail.quote_id, decision, detail.revision);
      setDetail(updated);
      setTotalBeforeEdit(decision.action === "edit" ? before : null);
      await refreshInbox().catch(reportInboxError);
      return true;
    } catch (e) {
      if (e instanceof ApiError && e.code === "stale_revision") {
        setError("This quote changed since you opened it. The latest version is shown below.");
        await refreshDetail();
      } else {
        setError(e instanceof ApiError ? `${e.message} (${e.code})` : "Request failed.");
      }
      return false;
    } finally {
      setBusy(false);
    }
  };

  const changeFilter = (next: InboxFilter) => {
    setFilter(next);
    setInboxLoaded(false);
  };

  const waiting = quotes.filter((q) => q.status === "awaiting_approval").length;
  const subline =
    !inboxLoaded || filter === "closed"
      ? "Nothing goes out without you."
      : waiting > 0
        ? `${waiting} ${waiting === 1 ? "quote needs" : "quotes need"} your OK. Nothing goes out without you.`
        : "Sab clear! No quotes are waiting for you.";

  if (authenticated === null) {
    return (
      <main className={`${PAGE} py-12`}>
        <Card className="mx-auto max-w-md p-8 text-center text-[15px] font-semibold text-ink-500">
          Checking owner session…
        </Card>
      </main>
    );
  }
  if (!authenticated) {
    return (
      <main className={`${PAGE} py-12`}>
        <Card className="mx-auto max-w-md overflow-hidden shadow-pop-lg">
          <div className="flex items-center gap-3.5 border-b-2 border-ink bg-marigold bg-dots px-6 py-5">
            <LogoMark size={48} />
            <div>
              <h1 className="font-display text-2xl font-extrabold tracking-[-0.02em]">Owner sign in</h1>
              <p className="text-sm font-bold">Business Ops is private.</p>
            </div>
          </div>
          <div className="flex flex-col gap-4 p-6">
            <p className="text-[15px] leading-relaxed text-ink-700">
              Sign in with the owner password configured on the backend.
            </p>
            {authError && <ErrorNote message={authError} />}
            <form className="flex flex-col gap-2" onSubmit={signIn}>
              <label className="text-sm font-extrabold" htmlFor="owner-password">
                Owner password
              </label>
              <input
                id="owner-password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="min-h-12 w-full rounded-[14px] border-2 border-line bg-mist px-3.5 text-base focus:border-ink focus:outline-none"
              />
              <Button type="submit" size="lg" className="mt-3 self-start">
                Sign in
              </Button>
            </form>
          </div>
        </Card>
      </main>
    );
  }

  return (
    <main className={`${PAGE} pb-8 pt-5`}>
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="flex flex-col gap-1.5">
          <h1 className="font-display text-[40px] font-extrabold leading-none tracking-[-0.04em]">Business Ops</h1>
          <p className="text-base text-ink-700">{subline}</p>
        </div>
        <Button variant="ghost" onClick={() => void signOut()}>
          <LogoutIcon size={18} />
          Sign out
        </Button>
      </div>

      <div className="mt-4 flex flex-wrap items-start gap-5">
        <section
          aria-labelledby="inbox-title"
          className="min-w-0 flex-[1_1_340px] overflow-hidden rounded-3xl border-2 border-ink bg-white"
        >
          <div className="flex items-center justify-between gap-3 px-4.5 pb-3 pt-4">
            <h2 id="inbox-title" className="font-display text-[22px] font-extrabold tracking-[-0.02em]">
              Inbox
            </h2>
            {waiting > 0 && (
              <span className="inline-flex min-h-7.5 items-center rounded-full border-2 border-ink bg-marigold px-3 text-[13px] font-extrabold">
                {waiting} {waiting === 1 ? "needs" : "need"} your OK
              </span>
            )}
          </div>
          {inboxError && (
            <div className="px-3.5 pb-3">
              <ErrorNote message={inboxError} />
            </div>
          )}
          <InboxTable
            quotes={quotes}
            filter={filter}
            onFilter={changeFilter}
            selectedId={selectedId}
            onSelect={select}
          />
          <p className="flex items-center gap-2 border-t-2 border-ink bg-mist px-4.5 py-3 text-[13px] font-semibold text-ink-500">
            <RefreshIcon size={16} />
            Refreshes every 3 seconds
          </p>
        </section>

        <div className="flex min-w-0 flex-[999_1_640px] flex-col">
          {detail ? (
            <QuoteInspector
              quote={detail}
              catalog={catalog}
              busy={busy}
              error={error}
              totalBeforeEdit={totalBeforeEdit}
              onDecide={decide}
            />
          ) : (
            <Card className="flex min-h-64 flex-col items-center justify-center gap-3 border-dashed p-8 text-center">
              <LogoMark size={44} />
              <p className="text-[15px] font-semibold text-ink-500">
                {selectedId ? "Loading…" : "Pick a quote from the inbox to review it."}
              </p>
            </Card>
          )}
        </div>
      </div>
    </main>
  );
}
