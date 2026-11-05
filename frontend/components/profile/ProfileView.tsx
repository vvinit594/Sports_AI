"use client";

import { DoorOpen } from "lucide-react";
import Link from "next/link";

import { AvatarBadge } from "@/components/app/AvatarBadge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useOnboarding } from "@/hooks/useOnboarding";
import { displayNameOrFallback, levelLabel } from "@/lib/personalization";
import { AVATARS } from "@/types/onboarding";

export function ProfileView() {
  const { state, hydrated } = useOnboarding();
  const name = displayNameOrFallback(state.displayName);
  const avatar = AVATARS.find((item) => item.id === state.avatar);

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
        My profile
      </p>
      <h1 className="mt-3 text-4xl font-bold uppercase sm:text-6xl">Your game identity</h1>
      <p className="mt-3 max-w-xl text-white/75">
        Preferences come from onboarding on this device. There is no account
        system in this release.
      </p>
      <Card className="mt-8 max-w-xl">
        <div className="flex items-center gap-4">
          <AvatarBadge name={name} avatarId={state.avatar} size="md" />
          <div>
            <p className="font-display text-3xl uppercase">{hydrated ? name : "…"}</p>
            <p className="text-sm text-muted">
              {avatar ? avatar.label : "Initials placeholder"}
            </p>
          </div>
        </div>
        <dl className="mt-6 grid gap-3 sm:grid-cols-2">
          <Item label="Sport" value="Cricket" />
          <Item label="Experience" value={levelLabel(state.selectedLevel)} />
          <Item
            label="Favourite team"
            value={state.favouriteTeam ?? "Not chosen"}
          />
          <Item
            label="Email"
            value={state.email.trim() ? state.email : "Not shared"}
          />
        </dl>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/onboarding">
            <Button>Edit setup</Button>
          </Link>
          <Link href="/home">
            <Button variant="outline">Back to insights</Button>
          </Link>
          <Link href="/" aria-label="Exit to the PulseIQ landing page">
            <Button variant="outline">
              <DoorOpen size={16} aria-hidden />
              Exit
            </Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <dt className="text-xs uppercase tracking-[0.16em] text-muted">{label}</dt>
      <dd className="mt-1 text-lg">{value}</dd>
    </div>
  );
}
