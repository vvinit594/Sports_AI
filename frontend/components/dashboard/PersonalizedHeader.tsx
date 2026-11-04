import { headerIntro, levelLabel } from "@/lib/personalization";
import type { OnboardingState } from "@/types/onboarding";

type PersonalizedHeaderProps = {
  profile: OnboardingState;
};

export function PersonalizedHeader({ profile }: PersonalizedHeaderProps) {
  const name = profile.displayName.trim() || "Player";

  return (
    <section className="pb-8">
      <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gold)]">
        Hey, {name}!
      </p>
      <h1 className="mt-3 max-w-3xl text-4xl font-bold uppercase leading-[0.95] sm:text-6xl">
        Ready to read the game?
      </h1>
      <div className="mt-5 flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-[0.16em]">
        <span className="rounded-full border border-white/15 bg-white/5 px-3 py-1">
          Sport · Cricket
        </span>
        <span className="rounded-full border border-[var(--electric)]/30 bg-[var(--electric)]/10 px-3 py-1 text-[var(--electric)]">
          {levelLabel(profile.selectedLevel)}
        </span>
        {profile.favouriteTeam ? (
          <span className="rounded-full border border-white/15 px-3 py-1 text-white/70">
            Supports {profile.favouriteTeam}
          </span>
        ) : null}
      </div>
      <p className="mt-4 max-w-2xl text-base text-white/75">
        {headerIntro(profile.selectedLevel, profile.favouriteTeam)}
      </p>
    </section>
  );
}
