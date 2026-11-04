"use client";

import Link from "next/link";

import { ExperienceLevelSelector } from "@/components/companion/ExperienceLevelSelector";
import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";
import { companionMomentHref } from "@/lib/live-query";
import { audienceVisibleLabel } from "@/lib/personalization";
import { useLiveIntelligence } from "@/hooks/useLiveIntelligence";

export function MatchAnalyst() {
  const {
    selectedMatchId,
    sequence,
    audience,
    setAudience,
    profileAudience,
    explaining,
    explanation,
    explainError,
    explain,
    currentState,
  } = useLiveIntelligence();

  if (!selectedMatchId) {
    return null;
  }

  return (
    <section className="rounded-[28px] border border-white/10 bg-[var(--ink-2)] p-4 md:p-6">
      <div className="flex items-center gap-3">
        <Logo compact />
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[var(--gold)]">
            PulseIQ match analyst
          </p>
          <h3 className="font-display text-2xl uppercase">Explain this moment</h3>
        </div>
      </div>
      <p className="mt-3 text-sm text-muted">
        Historical sample {selectedMatchId} · sequence {sequence}
        {currentState?.last_delivery
          ? ` · ${currentState.last_delivery.batter} vs ${currentState.last_delivery.bowler}`
          : ""}
        . Explanations run only when you ask. The companion is not a multi-turn backend memory.
      </p>

      <div className="mt-5">
        <ExperienceLevelSelector
          value={audience}
          onChange={setAudience}
          note="Temporary for this replay. It does not change your saved profile."
        />
        <p className="mt-2 text-[11px] text-muted">
          Saved profile default: {audienceVisibleLabel(profileAudience)}.
        </p>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <Button onClick={() => void explain()} disabled={explaining}>
          {explaining ? "Reading evidence…" : "Explain this moment"}
        </Button>
        <Link
          href={companionMomentHref(selectedMatchId, sequence, audience)}
          className="inline-flex h-11 items-center rounded-full border border-white/20 px-5 text-sm font-display font-semibold uppercase"
        >
          Ask PulseIQ about this moment
        </Link>
      </div>

      {explainError ? (
        <div className="mt-4 rounded-2xl border border-red-400/40 bg-red-950/20 p-4" role="alert">
          <p className="text-sm text-red-200">{explainError}</p>
          <button type="button" className="mt-2 text-sm text-[var(--gold)]" onClick={() => void explain()}>
            Retry
          </button>
        </div>
      ) : null}

      {explanation ? (
        <article className="mt-5 space-y-3 rounded-2xl border border-white/10 bg-black/30 p-4 text-sm">
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
            {explanation.source_match_id} · sequence {explanation.source_sequence} ·{" "}
            {explanation.model_provider}/{explanation.model_name} · {explanation.data_source}
            {explanation.grounded ? " · grounded" : ""}
          </p>
        </article>
      ) : null}
    </section>
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
