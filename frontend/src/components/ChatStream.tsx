"use client";

import { useEffect, useRef, useState } from "react";
import { fileUrl, type Message } from "@/lib/api";
import { Button } from "./ui";
import { VoiceRecorder } from "./VoiceRecorder";

export function ChatStream({
  messages,
  sending,
  onSend,
  onVoice,
}: {
  messages: Message[];
  sending: boolean;
  onSend: (text: string) => void;
  onVoice?: (audio: Blob) => void;
}) {
  const [draft, setDraft] = useState("");
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, sending]);

  const submit = () => {
    const text = draft.trim();
    if (!text || sending) return;
    onSend(text);
    setDraft("");
  };

  return (
    <div className="flex h-[calc(100vh-12rem)] min-h-[420px] flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 p-4">
        {messages.length === 0 && (
          <p className="pt-16 text-center text-sm text-slate-500">
            Send a message, or pick a scenario on the left.
          </p>
        )}
        {messages.map((m) => (
          <Bubble key={m.id} message={m} />
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-white px-3 py-2 text-sm text-slate-400 shadow-sm">
              typing…
            </div>
          </div>
        )}
        <div ref={bottom} />
      </div>
      <form
        className="flex gap-2 border-t border-slate-200 bg-white p-3"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={2}
          placeholder="Type a message… e.g. 50 black hoodies, DTF on back, M 20 L 20 XL 10"
          className="flex-1 resize-none rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
        />
        {onVoice && <VoiceRecorder disabled={sending} onRecorded={onVoice} />}
        <Button type="submit" disabled={sending || !draft.trim()} className="self-end">
          Send
        </Button>
      </form>
    </div>
  );
}

function Bubble({ message: m }: { message: Message }) {
  const mine = m.role === "customer";
  const pdf = fileUrl(m.pdf_url);
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm shadow-sm ${
          mine ? "bg-brand-600 text-white" : "bg-white text-slate-800"
        }`}
      >
        {m.text}
        {pdf && (
          <a
            href={pdf}
            target="_blank"
            rel="noreferrer"
            className="mt-2 flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-2 py-1.5 text-xs font-medium text-brand-700 hover:bg-brand-50"
          >
            📄 Download quotation PDF
          </a>
        )}
        <div className={`mt-1 text-[10px] ${mine ? "text-white/70" : "text-slate-400"}`}>
          {new Date(m.created_at + (m.created_at.endsWith("Z") ? "" : "Z")).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
          {m.kind === "voice" ? " · voice note" : ""}
        </div>
      </div>
    </div>
  );
}
