# PulseIQ frontend — Phase 4.1 / 4.2

Landing page, onboarding, and the Personalized Insights dashboard. The
dashboard reads the Phase 3 FastAPI catalog through a Next.js rewrite. The
full Match Intelligence view is not part of this milestone.

## Stack

- Next.js 15 App Router
- TypeScript
- Tailwind CSS 4
- Framer Motion
- Lucide React

## Run locally

From the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

The insights dashboard, AI Companion and Live Intelligence call `/api/v1/*`,
which Next.js proxies to `PULSEIQ_API_ORIGIN`. In development the rewrite
falls back to `http://127.0.0.1:8000` if the variable is unset. Start the
FastAPI server before opening `/home`, `/companion` or `/live`.

Production frontend hosts must set `PULSEIQ_API_ORIGIN` as a **server-side**
environment variable (not `NEXT_PUBLIC_*`). `next build` and `next start`
fail if it is missing so production never silently proxies to localhost.

## Checks

```powershell
npm run typecheck
npm run lint
npm run build
```
