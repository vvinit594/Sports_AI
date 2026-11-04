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

The insights dashboard and AI Companion call `/api/v1/*`, which Next.js
proxies to `PULSEIQ_API_ORIGIN` (default `http://127.0.0.1:8000`). Start the
FastAPI server before opening `/home` or `/companion`.

## Checks

```powershell
npm run typecheck
npm run lint
npm run build
```
