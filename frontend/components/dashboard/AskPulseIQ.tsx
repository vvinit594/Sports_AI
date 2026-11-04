"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { createExplanation, isPulseApiError } from "@/lib/api";
import { toAudienceLevel } from "@/lib/personalization";
import { useProgress } from "@/hooks/useProgress";
import type { ExplanationResponse, MatchSummary, MomentView } from "@/types/api";
import type { ExperienceLevel } from "@/types/onboarding";

type AskPulseIQProps = {
  level: ExperienceLevel | null;
  featured: MatchSummary | null;
  moment: MomentView | null;
};

type Question = {
  id: string;
  label: string;
  sequenceFromMoment: boolean;
};

const QUESTIONS: Question[] = [
  {
    id: "wicket",
    label: "Why was that wicket important?",
    sequenceFromMoment: true,
  },
  {
    id: "momentum",
    label: "How did the momentum change?",
    sequenceFromMoment: true,
  },
  {
    id: "situation",
    label: "Explain this match situation.",
    sequenceFromMoment: false,
  },
  {
    id: "rrr",
    label: "What does required run rate mean?",
    sequenceFromMoment: false,
  },
];

export function AskPulseIQ({ level, featured, moment }: AskPulseIQProps) {
  const { markAskedPulseIQ } = useProgress();
  const [active, setActive] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<ExplanationResponse | null>(null);
  const [glossary, setGlossary] = useState<string | null>(null);

  async function ask(question: Question) {
    setActive(question.id);
    setError(null);
    setAnswer(null);
    setGlossary(null);
    markAskedPulseIQ();

    if (question.id === "rrr") {
      setGlossary(
        level === "advanced"
          ? "Required run rate is runs remaining divided by overs remaining, copied from reconstructed chase state. PulseIQ does not let the language model calculate it."
          : "Required run rate is how many runs the batting team needs every over from this point. If they fall behind that number, the chase gets harder.",
      );
    }

    if (!featured) {
      setError("No historical match is loaded to ground an explanation.");
      return;
    }

    setLoading(true);
    try {
      const sequence =
        question.sequenceFromMoment && moment ? moment.sequence : undefined;
      const response = await createExplanation(
        featured.source_match_id,
        toAudienceLevel(level),
        sequence,
      );
      setAnswer(response);
    } catch (caught) {
      setError(
        isPulseApiError(caught)
          ? caught.message
          : "The explanation service could not answer from this match context.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mt-12">
      <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
        Grounded companion
      </p>
      <h2 className="mt-2 text-3xl font-bold uppercase">
        Ask PulseIQ — what do you want to understand?
      </h2>
      <p className="mt-2 max-w-2xl text-sm text-muted">
        These prompts call the existing explanation API with reconstructed match
        evidence. This is not an unrestricted cricket chatbot.
      </p>
      <div className="mt-5 flex flex-wrap gap-2">
        {QUESTIONS.map((question) => (
          <Button
            key={question.id}
            variant={active === question.id ? "primary" : "outline"}
            onClick={() => void ask(question)}
            disabled={loading}
          >
            {question.label}
          </Button>
        ))}
      </div>
      <Card className="mt-5">
        {loading ? <p className="text-sm text-muted">Reading reconstructed evidence…</p> : null}
        {error ? (
          <p className="text-sm text-red-300" role="alert">
            {error}
          </p>
        ) : null}
        {glossary ? <p className="text-sm text-white/80">{glossary}</p> : null}
        {answer ? (
          <div className={glossary ? "mt-4 space-y-2" : "space-y-2"}>
            <p className="text-sm text-white/85">{answer.summary}</p>
            <p className="text-sm text-white/70">{answer.what_happened}</p>
            <p className="text-sm text-white/70">{answer.why_it_matters}</p>
            <p className="text-xs text-muted">
              Grounded · {answer.source_match_id} · sequence {answer.source_sequence} ·{" "}
              {answer.model_provider}/{answer.model_name}
            </p>
          </div>
        ) : null}
        {!loading && !error && !answer && !glossary ? (
          <p className="text-sm text-muted">
            Pick a question to explain the featured historical match. Answers stay
            tied to catalogued evidence.
          </p>
        ) : null}
      </Card>
    </section>
  );
}
