"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";

import { isAudienceLevel } from "@/lib/live-query";
import { useCompanion } from "@/hooks/useCompanion";

export function CompanionHandoff() {
  const params = useSearchParams();
  const router = useRouter();
  const {
    hydrated,
    setSelectedMatch,
    setAudienceLevel,
    send,
    matchDetail,
    matchError,
  } = useCompanion();
  const applied = useRef(false);
  const sent = useRef(false);
  const match = params.get("match");
  const sequence = params.get("sequence");
  const level = params.get("level");

  useEffect(() => {
    if (!hydrated || applied.current || !match) {
      return;
    }
    applied.current = true;
    setSelectedMatch(match);
    if (isAudienceLevel(level)) {
      setAudienceLevel(level);
    }
  }, [hydrated, level, match, setAudienceLevel, setSelectedMatch]);

  useEffect(() => {
    if (!hydrated || !match || sent.current) {
      return;
    }
    const ready =
      matchDetail?.source_match_id === match || Boolean(matchError);
    if (!ready) {
      return;
    }
    sent.current = true;
    const parsed = sequence ? Number.parseInt(sequence, 10) : Number.NaN;
    const run =
      Number.isFinite(parsed) && !matchError
        ? send(`Explain sequence ${parsed}`)
        : Promise.resolve();
    void run.finally(() => {
      router.replace("/companion");
    });
  }, [hydrated, match, matchDetail, matchError, router, send, sequence]);

  return null;
}
