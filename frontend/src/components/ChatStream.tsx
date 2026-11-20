"use client";

import { useEffect, useRef, useState } from "react";
import { fileUrl, type Message } from "@/lib/api";
import { DownloadIcon, FileIcon, MicIcon, SendIcon } from "./icons";
import { LogoMark } from "./Logo";
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
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto bg-mist bg-dots-faint px-4 py-5 sm:px-6">
        {messages.length === 0 && (
          <div className="m-auto flex max-w-sm flex-col items-center gap-3 py-10 text-center">
            <LogoMark size={56} />
            <p className="font-display text-[26px] font-extrabold leading-tight tracking-[-0.02em]">
              Bolo, kya banwana hai?
            </p>
            <p className="text-[15px] leading-relaxed text-ink-700">
              Type it or send a voice note. Hinglish is fine. Or pick a scenario on the left.
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <Bubble key={m.id} message={m} first={i === 0} />
        ))}
        {sending && (
          <div className="flex items-center gap-1.5 self-start rounded-[20px] rounded-bl-md border-[1.5px] border-line bg-white px-4 py-3.5">
            <span className="sr-only">Sending…</span>
            {[0, 150, 300].map((delay) => (
              <span
                key={delay}
                aria-hidden="true"
                className="size-2 animate-bounce rounded-full bg-ink-500"
                style={{ animationDelay: `${delay}ms` }}
              />
            ))}
          </div>
        )}
        <div ref={bottom} />
      </div>
      <form
        className="flex items-end gap-2.5 border-t-2 border-ink bg-white px-3 py-3 sm:px-4"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label htmlFor="chat-message" className="sr-only">
          Message
        </label>
        <textarea
          id="chat-message"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={2}
          placeholder="Bolo, kya banwana hai? e.g. 50 black hoodies, DTF on back, M 20 L 20 XL 10"
          className="min-w-0 flex-1 resize-none rounded-2xl border-2 border-line bg-mist px-3.5 py-3 text-base leading-snug focus:border-ink focus:outline-none"
        />
        {onVoice && <VoiceRecorder disabled={sending} onRecorded={onVoice} />}
        <Button type="submit" size="lg" disabled={sending || !draft.trim()}>
          Send
          <SendIcon size={20} />
        </Button>
      </form>
    </div>
  );
}

function time(iso: string) {
  return new Date(iso + (iso.endsWith("Z") ? "" : "Z")).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function Bubble({ message: m, first }: { message: Message; first: boolean }) {
  const mine = m.role === "customer";
  const pdf = fileUrl(m.pdf_url);
  const push = first ? "mt-auto" : ""; // a short chat sits at the bottom, like a real one

  if (m.kind === "quote" && !mine) {
    return (
      <div
        className={`${push} w-full max-w-[460px] shrink-0 self-start overflow-hidden rounded-[22px] border-2 border-ink bg-white shadow-pop`}
      >
        <div className="flex items-center gap-2 border-b-2 border-ink bg-marigold bg-dots px-4 py-2.5">
          <FileIcon size={18} />
          <span className="font-display text-lg font-extrabold tracking-[-0.01em]">Your quotation</span>
        </div>
        <div className="flex flex-col gap-3 px-4 py-3.5">
          <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{m.text}</p>
          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
            {pdf && (
              <a
                href={pdf}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-11 items-center gap-2 rounded-xl border-2 border-ink bg-white px-3.5 text-sm font-extrabold shadow-pop-sm transition-[transform,box-shadow] hover:bg-mist active:translate-x-[3px] active:translate-y-[3px] active:shadow-none"
              >
                <DownloadIcon size={18} />
                Download quotation PDF
              </a>
            )}
            <span className="text-xs font-semibold text-ink-500">{time(m.created_at)}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`${push} max-w-[78%] shrink-0 whitespace-pre-wrap px-3.5 py-2.5 text-[15px] leading-relaxed ${
        mine
          ? "self-end rounded-[20px] rounded-br-md bg-rani text-white"
          : "self-start rounded-[20px] rounded-bl-md border-[1.5px] border-line bg-white"
      }`}
    >
      {m.kind === "voice" && (
        <span
          className={`mb-1 flex items-center gap-1.5 text-xs font-extrabold ${mine ? "text-white" : "text-peacock-700"}`}
        >
          <MicIcon size={14} />
          Voice note, transcribed
        </span>
      )}
      {m.text}
      {pdf && (
        <a
          href={pdf}
          target="_blank"
          rel="noreferrer"
          className="mt-2 flex min-h-11 items-center gap-2 rounded-xl border-2 border-ink bg-mist px-3 text-sm font-extrabold text-ink hover:bg-white"
        >
          <DownloadIcon size={18} />
          Download quotation PDF
        </a>
      )}
      <span className={`mt-1 block text-xs font-semibold ${mine ? "text-right text-white" : "text-ink-500"}`}>
        {time(m.created_at)}
      </span>
    </div>
  );
}
