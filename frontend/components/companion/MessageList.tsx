"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef } from "react";

import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";
import type { ChatMessage } from "@/types/companion";

type MessageListProps = {
  messages: ChatMessage[];
  pending: boolean;
  onRetry: (text: string) => void;
};

export function MessageList({ messages, pending, onRetry }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    endRef.current?.scrollIntoView({
      behavior: reduceMotion ? "auto" : "smooth",
      block: "end",
    });
  }, [messages.length, pending, reduceMotion]);

  return (
    <div className="space-y-4 px-4 py-6">
      {messages.map((message) =>
        message.role === "user" ? (
          <UserMessage key={message.id} message={message} reduceMotion={Boolean(reduceMotion)} />
        ) : (
          <AssistantMessage
            key={message.id}
            message={message}
            reduceMotion={Boolean(reduceMotion)}
            onRetry={onRetry}
          />
        ),
      )}
      {pending ? <TypingIndicator /> : null}
      <div ref={endRef} />
    </div>
  );
}

function UserMessage({
  message,
  reduceMotion,
}: {
  message: ChatMessage;
  reduceMotion: boolean;
}) {
  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="ml-auto max-w-[85%] rounded-[22px] border border-[var(--red)]/40 bg-[var(--surface)] px-4 py-3"
    >
      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      <time className="mt-2 block text-[11px] text-muted" dateTime={message.createdAt}>
        {new Date(message.createdAt).toLocaleTimeString()}
      </time>
    </motion.div>
  );
}

function AssistantMessage({
  message,
  reduceMotion,
  onRetry,
}: {
  message: ChatMessage;
  reduceMotion: boolean;
  onRetry: (text: string) => void;
}) {
  const explanation = message.response;
  return (
    <motion.article
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mr-auto max-w-[90%] rounded-[22px] border border-white/10 bg-[var(--ink-2)] px-4 py-4"
    >
      <div className="mb-3 flex items-center gap-2">
        <Logo compact />
        <p className="text-xs uppercase tracking-[0.16em] text-[var(--gold)]">
          PulseIQ
        </p>
      </div>
      {explanation ? (
        <div className="space-y-3 text-sm">
          <Section title="Summary" body={explanation.summary} />
          <Section title="What happened" body={explanation.what_happened} />
          <Section title="Why it matters" body={explanation.why_it_matters} />
          <Section title="Match context" body={explanation.match_context} />
          {explanation.key_factors.length > 0 ? (
            <div>
              <p className="text-xs uppercase tracking-[0.14em] text-muted">Key factors</p>
              <ul className="mt-1 list-disc space-y-1 pl-5">
                {explanation.key_factors.map((factor) => (
                  <li key={factor}>{factor}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <p className="text-xs text-muted">
            Historical sample · {explanation.source_match_id} · sequence{" "}
            {explanation.source_sequence} · {explanation.model_provider}/
            {explanation.model_name} · {explanation.data_source}
            {explanation.grounded ? " · grounded" : ""}
          </p>
        </div>
      ) : (
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      )}
      {message.kind === "knowledge" ? (
        <p className="mt-3 text-[11px] text-muted">Curated learning content · not match-model output</p>
      ) : null}
      {message.error && message.retryText ? (
        <div className="mt-3">
          <Button variant="outline" onClick={() => onRetry(message.retryText ?? "")}>
            Retry
          </Button>
        </div>
      ) : null}
      <time className="mt-2 block text-[11px] text-muted" dateTime={message.createdAt}>
        {new Date(message.createdAt).toLocaleTimeString()}
      </time>
    </motion.article>
  );
}

function Section({ title, body }: { title: string; body: string }) {
  if (!body.trim()) {
    return null;
  }
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.14em] text-muted">{title}</p>
      <p className="mt-1">{body}</p>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 text-sm text-muted" role="status">
      <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--red)]" />
      Reading reconstructed evidence…
    </div>
  );
}
