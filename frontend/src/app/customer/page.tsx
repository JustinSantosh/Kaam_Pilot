"use client";

import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { ChatStream } from "@/components/ChatStream";
import { StoreIcon } from "@/components/icons";
import { ScenarioPresets } from "@/components/ScenarioPresets";
import { DEMO_CUSTOMERS, SessionSwitcher } from "@/components/SessionSwitcher";
import { ErrorNote, StatusBadge } from "@/components/ui";
import { usePolling } from "@/hooks/usePolling";
import {
  api,
  ApiError,
  type ChatSendResponse,
  type Customer,
  type Message,
  type Scenario,
  type TurnStatus,
} from "@/lib/api";
import { resetConversation, serverSnapshot, snapshotFor, subscribe } from "@/lib/sessions";

const sessionSnapshot = snapshotFor(DEMO_CUSTOMERS.map((c) => c.id));

const PANEL = "flex flex-col gap-3 rounded-[22px] border-2 border-ink bg-white p-4";
const PANEL_TITLE = "font-display text-xl font-extrabold tracking-[-0.02em]";

export default function CustomerHub() {
  const [customerId, setCustomerId] = useState(DEMO_CUSTOMERS[0].id);
  const rawSessions = useSyncExternalStore(subscribe, sessionSnapshot, serverSnapshot);
  const sessions = useMemo(() => JSON.parse(rawSessions) as Record<string, string>, [rawSessions]);
  const conversationId = sessions[customerId];

  // Keyed by conversation, so switching customers never needs a reset.
  const [messagesByConv, setMessagesByConv] = useState<Record<string, Message[]>>({});
  const [statusByConv, setStatusByConv] = useState<Record<string, TurnStatus>>({});
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const customer = DEMO_CUSTOMERS.find((c) => c.id === customerId)!;
  const messages = useMemo(
    () => (conversationId ? (messagesByConv[conversationId] ?? []) : []),
    [conversationId, messagesByConv],
  );

  useEffect(() => {
    api
      .scenarios()
      .then(setScenarios)
      .catch((e: unknown) => {
        setError(
          e instanceof ApiError
            ? `${e.message} (${e.code})`
            : "Could not load the demo scenarios.",
        );
      });
  }, []);

  const poll = useCallback(async () => {
    if (!conversationId) return;
    const lastId = messages.at(-1)?.id ?? 0;
    const fresh = await api.messages(conversationId, lastId);
    if (fresh.length) {
      setMessagesByConv((prev) => {
        const have = prev[conversationId] ?? [];
        const last = have.at(-1)?.id ?? 0;
        return { ...prev, [conversationId]: [...have, ...fresh.filter((m) => m.id > last)] };
      });
    }
    setError(null);
  }, [conversationId, messages]);
  const reportPollError = useCallback((e: unknown) => {
    setError(
      e instanceof ApiError
        ? `${e.message} (${e.code})`
        : "Can't reach the backend. Is it running on port 8000?",
    );
  }, []);

  usePolling(poll, 2500, Boolean(conversationId), reportPollError);

  const send = (text: string) =>
    submit((who) => api.send(conversationId!, who, text));
  const sendVoice = (audio: Blob) =>
    submit((who) => api.sendAudio(conversationId!, who, audio));

  const submit = async (call: (who: Customer) => Promise<ChatSendResponse>) => {
    if (!conversationId) return;
    setSending(true);
    setError(null);
    try {
      const { name, phone, state } = customer;
      const result = await call({ name, phone, state });
      setStatusByConv((prev) => ({ ...prev, [conversationId]: result.status }));
      await poll();
    } catch (e) {
      setError(
        e instanceof ApiError
          ? `${e.message} (${e.code})`
          : "Can't reach the backend. Is it running on port 8000?",
      );
    } finally {
      setSending(false);
    }
  };

  const status = conversationId ? statusByConv[conversationId] : undefined;

  return (
    <main className="mx-auto flex max-w-[1440px] flex-wrap items-start gap-5 px-4 py-4 sm:px-8">
      <aside
        aria-label="Demo controls"
        className="flex min-w-0 flex-[1_1_290px] flex-col gap-4 lg:max-h-[calc(100vh-7.5rem)]"
      >
        <section aria-labelledby="who-title" className={PANEL}>
          <h2 id="who-title" className={PANEL_TITLE}>
            Who&apos;s chatting?
          </h2>
          <SessionSwitcher
            activeId={customerId}
            onSelect={setCustomerId}
            onReset={() => resetConversation(customerId)}
          />
        </section>
        <section aria-labelledby="scenario-title" className={`${PANEL} min-h-0 flex-1`}>
          <div className="flex items-baseline justify-between gap-2">
            <h2 id="scenario-title" className={PANEL_TITLE}>
              Try a scenario
            </h2>
            {scenarios.length > 0 && (
              <span className="text-[13px] font-bold text-ink-500">{scenarios.length} demos</span>
            )}
          </div>
          <div className="-mx-1 min-h-0 flex-1 overflow-y-auto px-1 pb-1">
            <ScenarioPresets scenarios={scenarios} disabled={sending} onSend={send} />
          </div>
        </section>
      </aside>

      <section
        aria-labelledby="chat-title"
        className="flex h-[calc(100vh-7.5rem)] min-h-[560px] min-w-0 flex-[999_1_560px] flex-col overflow-hidden rounded-3xl border-2 border-ink bg-white shadow-pop-lg"
      >
        <div className="flex flex-wrap items-center gap-x-3.5 gap-y-2 border-b-2 border-ink px-4 py-3.5 sm:px-5">
          <span className="flex size-11.5 shrink-0 items-center justify-center rounded-[14px] bg-ink text-marigold">
            <StoreIcon size={24} />
          </span>
          <span className="flex min-w-0 flex-1 flex-col gap-0.5">
            <h1 id="chat-title" className="font-display text-[22px] font-extrabold tracking-[-0.02em]">
              Chat with the business
            </h1>
            <span className="text-sm font-semibold text-ink-500">
              You&apos;re chatting as {customer.name} · {customer.city}
              {customer.state ? `, ${customer.state}` : ""}
            </span>
          </span>
          {status && <StatusBadge status={status} audience="customer" />}
        </div>
        {error && (
          <div className="border-b-2 border-ink px-4 py-3">
            <ErrorNote message={error} />
          </div>
        )}
        <ChatStream messages={messages} sending={sending} onSend={send} onVoice={sendVoice} />
        <p className="border-t-[1.5px] border-line bg-white px-5 py-2 text-xs font-semibold text-ink-500">
          Conversation <code>{conversationId ?? "…"}</code> · replies appear here as soon as the owner acts in
          Business Ops.
        </p>
      </section>
    </main>
  );
}
