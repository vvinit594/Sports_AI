type ProgressIndicatorProps = {
  step: 1 | 2 | 3;
};

export function ProgressIndicator({ step }: ProgressIndicatorProps) {
  const percent = (step / 3) * 100;

  return (
    <div className="space-y-3" aria-live="polite">
      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--gold)]">
        Step {step} of 3
      </p>
      <div
        className="h-1.5 overflow-hidden rounded-full bg-white/10"
        role="progressbar"
        aria-valuemin={1}
        aria-valuemax={3}
        aria-valuenow={step}
        aria-label={`Onboarding step ${step} of 3`}
      >
        <div
          className="progress-fill h-full rounded-full bg-[var(--red)]"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
