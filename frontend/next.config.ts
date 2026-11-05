import type { NextConfig } from "next";

const isProduction = process.env.NODE_ENV === "production";
const apiOrigin = process.env.PULSEIQ_API_ORIGIN?.trim();

if (!apiOrigin && isProduction) {
  throw new Error(
    "PULSEIQ_API_ORIGIN must be set for production builds and `next start`. " +
      "Configure it as a server-side environment variable on the frontend host " +
      "(Vercel/Netlify/etc. → Project settings → Environment Variables). " +
      "Do not use NEXT_PUBLIC_* — this value is read only by next.config.ts. " +
      "Example: https://pulseiq-api.example.com",
  );
}

const resolvedOrigin = apiOrigin || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${resolvedOrigin}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
