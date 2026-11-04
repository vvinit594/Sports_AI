type StatusPanelProps = {
  title: string;
  body: string;
  tone?: "default" | "error";
};

export function StatusPanel({ title, body, tone = "default" }: StatusPanelProps) {
  return (
    <div
      className={`rounded-[24px] border px-5 py-8 ${
        tone === "error"
          ? "border-red-400/40 bg-red-950/30"
          : "border-white/10 bg-[var(--surface)]"
      }`}
      role={tone === "error" ? "alert" : "status"}
    >
      <p className="font-display text-xl uppercase">{title}</p>
      <p className="mt-2 text-sm text-muted">{body}</p>
    </div>
  );
}

export function SectionSkeleton({ label }: { label: string }) {
  return (
    <div
      className="animate-pulse rounded-[24px] border border-white/10 bg-[var(--surface)] px-5 py-10"
      aria-busy="true"
      aria-label={`Loading ${label}`}
    >
      <div className="h-4 w-40 rounded bg-white/10" />
      <div className="mt-4 h-8 w-2/3 rounded bg-white/10" />
      <div className="mt-3 h-4 w-full rounded bg-white/5" />
    </div>
  );
}
