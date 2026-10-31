"use client";

import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { ChatStream } from "@/components/ChatStream";
import { ScenarioPresets } from "@/components/ScenarioPresets";
import { DEMO_CUSTOMERS, SessionSwitcher } from "@/components/SessionSwitcher";
import { Card, CardTitle, ErrorNote, StatusBadge } from "@/components/ui";
import { usePolling } from "@/hooks/usePolling";
import { api, ApiError, type Message, type Scenario, type TurnStatus } from "@/lib/api";
import { resetConversation, serverSnapshot, snapshotFor, subscribe } from "@/lib/sessions";

const sessionSnapshot = snapshotFor(DEMO_CUSTOMERS.map((c) => c.id));

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
      .catch(() => setScenarios([]));
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

  usePolling(poll, 2500, Boolean(conversationId));

  const send = async (text: string) => {
    if (!conversationId) return;
    setSending(true);
    setError(null);
    try {
      const { name, phone, state } = customer;
      const result = await api.send(conversationId, { name, phone, state }, text);
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
    <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
      <aside className="space-y-4">
        <Card>
          <CardTitle>Customer</CardTitle>
          <div className="p-3">
            <SessionSwitcher
              activeId={customerId}
              onSelect={setCustomerId}
              onReset={() => resetConversation(customerId)}
            />
          </div>
        </Card>
        <Card>
          <CardTitle>Scenarios</CardTitle>
          <div className="max-h-[50vh] overflow-y-auto p-3">
            <ScenarioPresets scenarios={scenarios} disabled={sending} onSend={send} />
          </div>
        </Card>
      </aside>

      <section className="space-y-3">
        <ErrorNote message={error} />
        <Card className="overflow-hidden">
          <CardTitle aside={status && <StatusBadge status={status} />}>
            Chat with the business · {customer.name}
          </CardTitle>
          <ChatStream messages={messages} sending={sending} onSend={send} />
        </Card>
        <p className="text-xs text-slate-500">
          Conversation <code>{conversationId ?? "…"}</code>. Replies appear here as soon as the
          owner acts in Business Ops.
        </p>
      </section>
    </div>
  );
}
