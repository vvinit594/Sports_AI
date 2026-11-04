import Link from "next/link";

export function AppFooter() {
  return (
    <footer className="mt-16 border-t border-white/10 bg-black/40">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-10 md:flex-row md:items-start md:justify-between md:px-8">
        <div>
          <p className="font-display text-xl tracking-[0.16em]">
            PULSE<span className="text-[var(--red)]">IQ</span>
          </p>
          <p className="mt-2 max-w-md text-sm text-muted">
            Historical sample cricket intelligence. Not a live scoreboard and not
            a production forecasting product.
          </p>
        </div>
        <nav className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/75">
          <Link href="/about" className="hover:text-white">
            About
          </Link>
          <Link href="/data" className="hover:text-white">
            Data and methodology
          </Link>
          <Link href="/profile" className="hover:text-white">
            User profile
          </Link>
        </nav>
      </div>
      <p className="mx-auto max-w-6xl px-5 pb-8 text-xs text-muted md:px-8">
        The current match library and model insights are based on official
        Cricsheet T20 sample files. Chase probabilities use a small training
        corpus and are not production-accurate forecasts.
      </p>
    </footer>
  );
}
