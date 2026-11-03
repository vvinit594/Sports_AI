export function StadiumBackdrop({ className = "" }: { className?: string }) {
  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}>
      <div className="floodlight floodlight-left" />
      <div className="floodlight floodlight-right" />
      <svg
        className="hero-zoom absolute -bottom-[18%] left-1/2 h-[72%] w-[130%] max-w-none -translate-x-1/2 opacity-80"
        viewBox="0 0 1200 700"
        aria-hidden
      >
        <defs>
          <radialGradient id="pitch" cx="50%" cy="50%" r="60%">
            <stop offset="0%" stopColor="#2f9e5c" />
            <stop offset="70%" stopColor="#146338" />
            <stop offset="100%" stopColor="#0b1d14" />
          </radialGradient>
        </defs>
        <ellipse cx="600" cy="430" rx="520" ry="210" fill="url(#pitch)" />
        <ellipse
          cx="600"
          cy="430"
          rx="420"
          ry="160"
          fill="none"
          stroke="rgba(255,255,255,0.18)"
          strokeWidth="3"
        />
        <ellipse
          cx="600"
          cy="430"
          rx="170"
          ry="64"
          fill="none"
          stroke="rgba(255,255,255,0.28)"
          strokeWidth="2"
        />
        <rect
          x="560"
          y="360"
          width="80"
          height="140"
          rx="8"
          fill="rgba(232, 210, 140, 0.35)"
          stroke="rgba(255,255,255,0.4)"
        />
        <line
          x1="600"
          y1="368"
          x2="600"
          y2="492"
          stroke="rgba(255,255,255,0.55)"
          strokeWidth="2"
        />
      </svg>
      <div className="absolute inset-0 bg-gradient-to-b from-black/35 via-black/45 to-[var(--ink)]" />
    </div>
  );
}
