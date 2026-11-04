"use client";

import { useRef, useState } from "react";
import { Button } from "./ui";

const MAX_SECONDS = 120;

/** Records a voice note in the browser and hands the blob to `onRecorded` (Phase 10). */
export function VoiceRecorder({
  disabled,
  onRecorded,
}: {
  disabled: boolean;
  onRecorded: (audio: Blob) => void;
}) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<number | null>(null);
  const cancelled = useRef<{ value: boolean } | null>(null);

  const stop = () => {
    recorder.current?.stop();
    if (timer.current) window.clearInterval(timer.current);
    timer.current = null;
    setRecording(false);
  };

  const cancel = () => {
    if (cancelled.current) cancelled.current.value = true;
    stop();
  };

  const start = async () => {
    setError(null);
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
        setError("Voice recording is not supported in this browser.");
        return;
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      const chunks: Blob[] = [];
      const recordingState = { value: false };
      cancelled.current = recordingState;
      rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
        if (!recordingState.value && blob.size > 0) onRecorded(blob);
      };
      recorder.current = rec;
      rec.start();
      setSeconds(0);
      setRecording(true);
      timer.current = window.setInterval(() => {
        setSeconds((s) => {
          if (s + 1 >= MAX_SECONDS) stop();
          return s + 1;
        });
      }, 1000);
    } catch {
      setError("Microphone not available");
    }
  };

  return (
    <div className="flex flex-col items-end self-end">
      {recording ? (
        <div className="flex items-center gap-2">
          <Button variant="ghost" onClick={cancel} title="Cancel recording">
            Cancel
          </Button>
          <Button variant="danger" onClick={stop} title="Stop and send">
            ■ {seconds}s
          </Button>
        </div>
      ) : (
        <Button
          variant="secondary"
          onClick={start}
          disabled={disabled}
          title="Record a voice note"
          aria-label="Record a voice note"
        >
          🎤
        </Button>
      )}
      {error && <span className="mt-1 text-[10px] text-red-600">{error}</span>}
    </div>
  );
}
