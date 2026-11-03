type LogoProps = {
  compact?: boolean;
};

export function Logo({ compact = false }: LogoProps) {
  return (
    <span className="inline-flex items-center gap-2.5 text-white">
      <span
        aria-hidden
        className="relative grid h-9 w-9 place-items-center rounded-full bg-[var(--red)] shadow-[0_0_18px_var(--glow)]"
      >
        <span className="h-5 w-5 rounded-full border-[3px] border-white/90" />
        <span className="absolute inset-x-1 top-1/2 h-0.5 -translate-y-1/2 bg-white/90" />
      </span>
      {compact ? (
        <span className="sr-only">PulseIQ</span>
      ) : (
        <span className="font-display text-2xl tracking-[0.14em]">
          PULSE<span className="text-[var(--red)]">IQ</span>
        </span>
      )}
    </span>
  );
}
