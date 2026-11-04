import type { Metadata } from "next";

import { DataContent } from "@/components/about/AboutContent";

export const metadata: Metadata = {
  title: "PulseIQ — Data and methodology",
};

export default function DataPage() {
  return <DataContent />;
}
