"use client";

import { Send } from "lucide-react";
import { useState, type KeyboardEvent } from "react";

type MessageComposerProps = {
  disabled?: boolean;
  pending?: boolean;
  onSend: (text: string) => void;
};

export function MessageComposer({ disabled, pending, onSend }: MessageComposerProps) {
  const [value, setValue] = useState("");
  const empty = value.trim().length === 0;
  const blocked = disabled || pending || empty;

  function submit() {
    if (blocked) {
      return;
    }
    const text = value;
    setValue("");
    onSend(text);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form
      className="border-t border-white/10 bg-[var(--ink)]/95 p-4"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <label htmlFor="companion-composer" className="sr-only">
        Message PulseIQ
      </label>
      <div className="flex items-end gap-3">
        <textarea
          id="companion-composer"
          rows={2}
          value={value}
          disabled={disabled || pending}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={
            pending ? "Waiting for PulseIQ…" : "Ask a cricket question or a match situation…"
          }
          className="max-h-40 min-h-[52px] flex-1 resize-y rounded-2xl border border-white/15 bg-black/40 px-4 py-3 text-sm outline-none focus:border-[var(--gold)]"
        />
        <button
          type="submit"
          disabled={blocked}
          aria-label="Send message"
          className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-[var(--red)] text-white disabled:opacity-40"
        >
          <Send size={18} />
        </button>
      </div>
      <p className="mt-2 text-[11px] text-muted">
        Enter to send · Shift+Enter for a new line. If a match explanation fails, use Retry on that message.
      </p>
    </form>
  );
}
