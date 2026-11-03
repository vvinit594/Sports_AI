const steps = [
  { n: "01", title: "Choose your sport", copy: "Start with cricket. More arenas unlock soon." },
  {
    n: "02",
    title: "Select your level",
    copy: "Beginner, intermediate or advanced — we match the insight depth.",
  },
  {
    n: "03",
    title: "Explore match intelligence",
    copy: "Replay historical matches, moments and grounded AI explanations.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-[var(--ink-2)] px-5 py-24 md:px-8">
      <div className="mx-auto max-w-6xl">
        <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
          How it works
        </p>
        <h2 className="mt-3 text-3xl font-bold uppercase sm:text-5xl">Three moves to kick off.</h2>
        <ol className="mt-12 grid gap-5 md:grid-cols-3">
          {steps.map((step) => (
            <li
              key={step.n}
              className="rounded-[var(--radius-lg)] border border-white/10 bg-black/20 p-6"
            >
              <p className="font-display text-4xl text-[var(--red)]">{step.n}</p>
              <h3 className="mt-4 text-xl font-semibold">{step.title}</h3>
              <p className="mt-3 text-sm leading-6 text-muted">{step.copy}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
