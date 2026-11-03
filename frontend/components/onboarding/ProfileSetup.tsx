"use client";

import { Input } from "@/components/ui/Input";
import { AVATARS, FAVOURITE_TEAMS, type OnboardingState } from "@/types/onboarding";

type ProfileSetupProps = {
  state: OnboardingState;
  nameError: string | null;
  emailError: string | null;
  onChange: (patch: Partial<OnboardingState>) => void;
};

export function ProfileSetup({
  state,
  nameError,
  emailError,
  onChange,
}: ProfileSetupProps) {
  const initials = state.displayName.trim().slice(0, 2).toUpperCase() || "PQ";
  const avatar = AVATARS.find((item) => item.id === state.avatar);

  return (
    <div>
      <h1 className="text-3xl font-bold uppercase sm:text-5xl">Let&apos;s Get to Know You!</h1>
      <p className="mt-3 max-w-xl text-muted">
        Set up your profile and make your PulseIQ experience yours.
      </p>
      <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="space-y-5">
          <Input
            label="Display name"
            name="displayName"
            value={state.displayName}
            error={nameError}
            placeholder="Your name on the field"
            autoComplete="nickname"
            onChange={(event) => onChange({ displayName: event.target.value })}
          />
          <Input
            label="Email address"
            name="email"
            type="email"
            optional
            value={state.email}
            error={emailError}
            placeholder="you@email.com"
            autoComplete="email"
            onChange={(event) => onChange({ email: event.target.value })}
          />
          <fieldset>
            <legend className="mb-3 flex items-baseline justify-between text-sm font-medium">
              <span>Profile avatar</span>
              <span className="text-xs text-muted">Optional</span>
            </legend>
            <div className="flex flex-wrap gap-3">
              {AVATARS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={state.avatar === item.id}
                  aria-label={item.label}
                  onClick={() =>
                    onChange({ avatar: state.avatar === item.id ? null : item.id })
                  }
                  className={`h-12 w-12 rounded-full border-2 transition ${
                    state.avatar === item.id
                      ? "scale-110 border-white"
                      : "border-transparent"
                  }`}
                  style={{ background: item.accent }}
                />
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend className="mb-3 flex items-baseline justify-between text-sm font-medium">
              <span>Favourite cricket team</span>
              <span className="text-xs text-muted">Optional</span>
            </legend>
            <div className="flex flex-wrap gap-2">
              {FAVOURITE_TEAMS.map((team) => {
                const active = state.favouriteTeam === team;
                return (
                  <button
                    key={team}
                    type="button"
                    aria-pressed={active}
                    onClick={() =>
                      onChange({ favouriteTeam: active ? null : team })
                    }
                    className={`rounded-full border px-3 py-2 text-sm transition ${
                      active
                        ? "border-[var(--red)] bg-[var(--red)] text-white"
                        : "border-white/15 bg-white/5 hover:border-white/40"
                    }`}
                  >
                    {team}
                  </button>
                );
              })}
            </div>
          </fieldset>
        </div>
        <aside className="rounded-[28px] border border-white/10 bg-[var(--surface)] p-5">
          <p className="text-xs uppercase tracking-[0.24em] text-muted">Profile preview</p>
          <div
            className="mt-5 grid h-20 w-20 place-items-center rounded-full font-display text-2xl"
            style={{ background: avatar?.accent ?? "#2a3140" }}
          >
            {initials}
          </div>
          <p className="mt-4 text-xl font-semibold">
            {state.displayName.trim() || "Your name"}
          </p>
          <p className="text-sm text-muted">{state.email.trim() || "No email yet"}</p>
          <p className="mt-4 text-sm text-muted">
            {state.favouriteTeam
              ? `Supports ${state.favouriteTeam}`
              : "Pick a side when you are ready"}
          </p>
        </aside>
      </div>
    </div>
  );
}
