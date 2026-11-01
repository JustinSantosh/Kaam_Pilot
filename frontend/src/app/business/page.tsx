"use client";

import { useCallback, useEffect, useState } from "react";
import { InboxTable, type InboxFilter } from "@/components/InboxTable";
import { QuoteInspector } from "@/components/QuoteInspector";
import { Card, CardTitle, ErrorNote } from "@/components/ui";
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
    api.catalog().then(setCatalog).catch(() => setCatalog([]));
  }, []);

  const refreshInbox = useCallback(async () => {
    try {
      setQuotes(await api.inbox(filter));
      setInboxError(null);
    } catch {
      setInboxError("Can't reach the backend. Is it running on port 8000?");
    }
  }, [filter]);

  const refreshDetail = useCallback(async () => {
    if (selectedId) setDetail(await api.quote(selectedId));
  }, [selectedId]);

  usePolling(refreshInbox, 3000);
  usePolling(refreshDetail, 5000, Boolean(selectedId));

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
      await refreshInbox();
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

  return (
    <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
      <aside className="space-y-3">
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
