import type { ExperienceLevel } from "@/types/onboarding";
import type { AudienceLevel, MatchState } from "@/types/api";

export function toAudienceLevel(level: ExperienceLevel | null): AudienceLevel {
  if (level === "advanced") {
    return "advanced";
  }
  if (level === "intermediate") {
    return "casual";
  }
  return "beginner";
}

export function audienceVisibleLabel(level: AudienceLevel): string {
  if (level === "advanced") {
    return "Advanced";
  }
  if (level === "casual") {
    return "Intermediate";
  }
  return "Beginner";
}

export function displayNameOrFallback(name: string): string {
  const trimmed = name.trim();
  return trimmed || "Player";
}

export function levelLabel(level: ExperienceLevel | null): string {
  if (level === "intermediate") {
    return "Intermediate";
  }
  if (level === "advanced") {
    return "Advanced";
  }
  return "Beginner";
}

export function headerIntro(
  level: ExperienceLevel | null,
  favouriteTeam: string | null,
): string {
  const team = favouriteTeam ? ` ${favouriteTeam} in the mix,` : "";
  if (level === "advanced") {
    return `Advanced read.${team} Reconstructed chase state, required-rate maths and model probability movement when the artifact is loaded — never invented.`;
  }
  if (level === "intermediate") {
    return `Tactical layer on.${team} We'll surface turning points, required run rate and why momentum flipped in these historical samples.`;
  }
  return `We'll keep the cricket plain.${team} Big moments, simple terms, and a story you can follow without a scoring app.`;
}

export type LearnTopic = {
  id: string;
  title: string;
  concept: string;
  body: string;
  evidence: string | null;
};

export function learnTopicFromState(
  level: ExperienceLevel | null,
  state: MatchState | null,
): LearnTopic {
  const requiredRunRate = state?.required_run_rate;
  const ballsRemaining = state?.balls_remaining;
  const chaseIsLive =
    requiredRunRate != null &&
    requiredRunRate > 0 &&
    ballsRemaining != null &&
    ballsRemaining > 0 &&
    state != null &&
    !state.match_complete;

  if (chaseIsLive && requiredRunRate != null && ballsRemaining != null) {
    const oversLeft = (ballsRemaining / 6).toFixed(1);
    if (level === "advanced") {
      return {
        id: "required-run-rate",
        title: "Required run rate",
        concept: "Chase equation",
        body: "Required run rate is runs still needed divided by overs remaining. PulseIQ copies it from reconstructed match state; it is not estimated by the language model.",
        evidence: `Measured RRR ${requiredRunRate.toFixed(2)} with ${ballsRemaining} balls remaining (${oversLeft} ov). Target ${state.target ?? "not in this state"}.`,
      };
    }
    if (level === "intermediate") {
      return {
        id: "required-run-rate",
        title: "Required run rate",
        concept: "Pressure on the chase",
        body: "Required run rate is how fast the batting side must score from here. Compare it with the current run rate to feel whether the chase is on track.",
        evidence: `This reconstructed chase sits at RRR ${requiredRunRate.toFixed(2)} with ${oversLeft} overs left.`,
      };
    }
    return {
      id: "required-run-rate",
      title: "Required run rate",
      concept: "How fast do they need to score?",
      body: "Think of required run rate as the speed the batting team must keep up. If they need 12 an over, every quiet ball makes the next one harder.",
      evidence: `In this sample they needed ${requiredRunRate.toFixed(1)} runs per over with ${oversLeft} overs still to go.`,
    };
  }

  if (state?.wickets_remaining != null) {
    if (level === "advanced") {
      return {
        id: "wickets-in-hand",
        title: "Wickets in hand",
        concept: "Resources remaining",
        body: "Wickets remaining are batting resources. They bound how aggressively a side can chase without collapsing the innings.",
        evidence: `${state.batting_team ?? "The batting side"} had ${state.wickets_remaining} wickets remaining at sequence ${state.sequence}.`,
      };
    }
    if (level === "intermediate") {
      return {
        id: "wickets-in-hand",
        title: "Wickets in hand",
        concept: "Who can still bat?",
        body: "Wickets in hand are the batters still to come. More wickets usually means the batting side can take more risks.",
        evidence: `${state.wickets_remaining} wickets were still available in this reconstructed innings.`,
      };
    }
    return {
      id: "wickets-in-hand",
      title: "Wickets in hand",
      concept: "How many batters are left?",
      body: "Each wicket is one batter out. Wickets in hand means how many chances the team still has to score.",
      evidence: `This innings still had ${state.wickets_remaining} wickets in hand.`,
    };
  }

  return {
    id: "historical-replay",
    title: "Historical replay",
    concept: "Sample match, not live cricket",
    body:
      level === "advanced"
        ? "PulseIQ reconstructs completed Cricsheet samples ball by ball. Missing metrics stay empty rather than being filled in."
        : "These matches already finished. PulseIQ replays the recorded balls so you can learn from real situations without pretending they are live.",
    evidence: state
      ? `Latest reconstructed sequence ${state.sequence}${state.overs ? `, ${state.overs} overs` : ""}.`
      : "Open a match to attach this lesson to reconstructed state.",
  };
}

export function momentCopy(level: ExperienceLevel | null): {
  kicker: string;
  empty: string;
  unavailable: string;
} {
  if (level === "advanced") {
    return {
      kicker: "Detector output from chase win-probability swings, not a second classifier.",
      empty: "The detector ran, but this sample did not emit a moment at the configured thresholds.",
      unavailable: "Moments need a loaded model artifact. Nothing is invented while it is missing.",
    };
  }
  if (level === "intermediate") {
    return {
      kicker: "Turning points PulseIQ marked from reconstructed momentum, not a live feed.",
      empty: "No significant moment was flagged in the samples loaded for this view.",
      unavailable: "Moment detection is unavailable until the chase model file is loaded.",
    };
  }
  return {
    kicker: "A big moment from a finished match, explained in plain cricket.",
    empty: "No highlight moment is ready in the historical sample yet.",
    unavailable: "We can't show detected moments until the cricket model file is available.",
  };
}
