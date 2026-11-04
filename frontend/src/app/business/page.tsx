"use client";

import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { InboxTable, type InboxFilter } from "@/components/InboxTable";
import { QuoteInspector } from "@/components/QuoteInspector";
import { Button, Card, CardTitle, ErrorNote } from "@/components/ui";
import { usePolling } from "@/hooks/usePolling";
import {
  api,
  ApiError,
  type CatalogOption,
  type Decision,
  type QuoteDetail,
  type QuoteSummary,
} from "@/lib/api";

export default function BusinessOps() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [filter, setFilter] = useState<InboxFilter>("awaiting_approval");
  const [quotes, setQuotes] = useState<QuoteSummary[]>([]);
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

  const waiting = quotes.filter((q) => q.status === "awaiting_approval").length;

  if (authenticated === null) {
    return <Card className="p-8 text-center text-sm text-slate-500">Checking owner session…</Card>;
  }
  if (!authenticated) {
    return (
      <Card className="mx-auto max-w-md p-6">
        <h1 className="text-xl font-semibold text-slate-900">Owner sign in</h1>
        <p className="mt-1 text-sm text-slate-600">
          Business Ops is private. Sign in with the owner password configured on the backend.
        </p>
        {authError && <ErrorNote message={authError} />}
        <form className="mt-5 space-y-3" onSubmit={signIn}>
          <label className="block text-sm font-medium text-slate-700" htmlFor="owner-password">
            Owner password
          </label>
          <input
            id="owner-password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <Button type="submit">Sign in</Button>
        </form>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
      <aside className="space-y-3">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold text-slate-900">Business Ops</h1>
          <Button variant="ghost" onClick={() => void signOut()}>
            Sign out
          </Button>
        </div>
        <ErrorNote message={inboxError} />
        <Card className="overflow-hidden">
          <CardTitle
            aside={
              filter === "awaiting_approval" && waiting > 0 ? (
                <span className="rounded-full bg-amber-500 px-2 py-0.5 text-xs font-semibold text-white">
                  {waiting}
                </span>
              ) : null
            }
          >
            Quotes
          </CardTitle>
          <InboxTable
            quotes={quotes}
            filter={filter}
            onFilter={setFilter}
            selectedId={selectedId}
            onSelect={select}
          />
        </Card>
      </aside>
      <section>
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
          <Card className="flex h-64 items-center justify-center">
            <p className="text-sm text-slate-500">
              {selectedId ? "Loading…" : "Select a quote to review it."}
            </p>
          </Card>
        )}
      </section>
    </div>
  );
}
