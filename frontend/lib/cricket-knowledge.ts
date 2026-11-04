import type { AudienceLevel } from "@/types/api";

export type KnowledgeTopic = {
  id: string;
  title: string;
  keywords: string[];
  answers: Record<AudienceLevel, string>;
};

export const CRICKET_KNOWLEDGE: KnowledgeTopic[] = [
  {
    id: "wicket",
    title: "Wicket",
    keywords: ["wicket", "dismissal", "how is someone out", "getting out"],
    answers: {
      beginner:
        "A wicket is when a batter is out. Ten wickets end an innings in a normal match. The word also describes the three stumps the bowler aims at.",
      casual:
        "A wicket is a dismissal. Losing one reduces batting resources and can swing chase pressure. Teams also talk about “wickets in hand” — how many batters are still to come.",
      advanced:
        "A counting wicket is a dismissal that reduces wickets remaining. PulseIQ copies that from reconstructed deliveries (`counts_as_wicket`). It is not inferred by the language model. Ten counting wickets complete a standard innings.",
    },
  },
  {
    id: "required-run-rate",
    title: "Required run rate",
    keywords: ["required run rate", "rrr", "need to score", "asking rate"],
    answers: {
      beginner:
        "Required run rate is how many runs the batting team must score each over from now on to win. If they fall behind that number, the chase gets harder.",
      casual:
        "Required run rate (RRR) is runs still needed divided by overs remaining. Compare it with current run rate: if RRR climbs above what the batting side is scoring, pressure rises.",
      advanced:
        "RRR = runs remaining ÷ overs remaining. PulseIQ reads it from reconstructed chase state; the explainer does not calculate it. A jump in RRR after a quiet over or a wicket is a chase-equation shift.",
    },
  },
  {
    id: "current-run-rate",
    title: "Current run rate",
    keywords: ["current run rate", "crr", "scoring rate", "run rate versus"],
    answers: {
      beginner:
        "Current run rate is how fast the batting team has scored so far — runs divided by overs already bowled.",
      casual:
        "Current run rate (CRR) is scoring pace to this point. In a chase you compare CRR with required run rate to see if the batting side is on track.",
      advanced:
        "CRR = innings runs ÷ overs completed (from legal balls). It is a descriptive rate, not a forecast. PulseIQ copies CRR from match state when the field is present.",
    },
  },
  {
    id: "powerplay",
    title: "Powerplay",
    keywords: ["powerplay", "power play", "fielding restriction", "first six overs"],
    answers: {
      beginner:
        "A powerplay is a period when only a few fielders can stand far from the bat. In T20, that is usually the first six overs, so batting teams often try to score quickly.",
      casual:
        "T20 men’s internationals and most T20 leagues use a six-over powerplay with a maximum of two fielders outside the 30-yard circle. Extra fielders then go back, so scoring shots into the deep get harder.",
      advanced:
        "Under current T20 playing conditions the fielding side may have at most two fielders outside the 30-yard circle in the first six overs. After that, five may be outside. PulseIQ does not currently expose powerplay phase as its own API field.",
    },
  },
  {
    id: "lbw",
    title: "LBW",
    keywords: ["lbw", "leg before", "leg before wicket"],
    answers: {
      beginner:
        "LBW means leg before wicket. The bowler can appeal if the ball hits the batter’s pad, would have hit the stumps, and the batter did not hit it first with the bat.",
      casual:
        "LBW requires the ball to pitch in line or outside off (not outside leg), to hit the batter in line with the stumps (unless playing a shot), and to be going on to hit the stumps. Umpires and DRS apply those laws.",
      advanced:
        "Law 36: the ball must not pitch outside leg, the impact point and projected path must satisfy the in-line exceptions, and there must be no first contact with the bat. DRS “umpire’s call” keeps the on-field decision if the ball only clips the stumps on projection.",
    },
  },
  {
    id: "super-over",
    title: "Super over",
    keywords: ["super over", "superover", "tied match", "tie breaker"],
    answers: {
      beginner:
        "If a limited-overs match is tied, some competitions play a super over — each team faces a few extra balls to decide a winner.",
      casual:
        "A super over is a one-over-per-side tiebreaker used in many T20s. Each side bats one over; the higher score wins. Further super overs or boundary counts can apply if it is still level, depending on the event rules.",
      advanced:
        "Playing conditions vary by tournament. Commonly each side faces one over with two wickets available. PulseIQ reconstructs super-over innings when they exist in the Cricsheet file (`is_super_over`). It does not invent a super over that is absent from the source.",
    },
  },
  {
    id: "drs",
    title: "DRS",
    keywords: ["drs", "decision review", "umpire's call", "review system"],
    answers: {
      beginner:
        "DRS is the Decision Review System. Teams can ask for a video and technology check if they think an umpire’s decision was wrong.",
      casual:
        "Each side usually has a limited number of unsuccessful reviews. Ball-tracking, UltraEdge and replay are used. If the technology is inconclusive, the original on-field call stands.",
      advanced:
        "ICC DRS uses ball-tracking and edge detection. “Umpire’s call” retains the on-field decision when the projection only marginally hits or misses the stumps. PulseIQ stores review metadata from Cricsheet when present; this learning answer is not a live review feed.",
    },
  },
  {
    id: "over",
    title: "Over",
    keywords: ["what is an over", "six balls", "over in cricket"],
    answers: {
      beginner:
        "An over is six legal balls from one bowler. Wides and no-balls do not count as those six, so the over can last longer.",
      casual:
        "A standard over is six legal deliveries. Extras that are not legal (wides, no-balls) are re-bowled. Bowlers cannot bowl consecutive overs.",
      advanced:
        "Legal balls increment the over. PulseIQ reconstructs `overs` as a cricket string (for example 18.1) from legal-ball counts. Miscounted overs in the source file are preserved, not “corrected”.",
    },
  },
  {
    id: "innings",
    title: "Innings",
    keywords: ["innings", "inning", "batting innings"],
    answers: {
      beginner:
        "An innings is a team’s turn to bat. In T20 each side usually has one innings of up to 20 overs.",
      casual:
        "A T20 innings ends at 20 overs, 10 wickets, or when the chase target is reached. Super overs are extra innings in the source file when they were played.",
      advanced:
        "PulseIQ numbers innings as they appear in the reconstructed match. Super overs are flagged with `is_super_over`. Completion reasons come from the match engine, not from the explainer.",
    },
  },
  {
    id: "yorker",
    title: "Yorker",
    keywords: ["yorker", "full toss at toes", "at the blockhole"],
    answers: {
      beginner:
        "A yorker is a very full ball that lands near the batter’s feet. It is hard to hit in the air.",
      casual:
        "Yorkers are a death-over weapon: full at the crease, cramping swing. A missed yorker becomes a full toss, which is easier to score from.",
      advanced:
        "A yorker is a length description, not an official dismissal type. PulseIQ does not label yorkers in reconstructed state; that would be an extra classifier we do not have.",
    },
  },
  {
    id: "googly",
    title: "Googly",
    keywords: ["googly", "wrong 'un", "wrongun"],
    answers: {
      beginner:
        "A googly is a spinning delivery from a wrist-spinner that turns the other way from a normal leg-break, to surprise the batter.",
      casual:
        "A right-arm leg-spinner’s googly turns from off to leg for a right-hand batter — the opposite of the stock ball. It is a deception option, not a dismissal type.",
      advanced:
        "Googly is a bowling style, not a Cricsheet event flag. PulseIQ will not claim a delivery was a googly unless that appears in source text, which these samples generally do not record.",
    },
  },
  {
    id: "maiden",
    title: "Maiden over",
    keywords: ["maiden", "maiden over"],
    answers: {
      beginner:
        "A maiden over is an over where the batting team scores no runs off the bat or extras that count against the bowler.",
      casual:
        "A maiden is six legal balls for zero runs credited to the bowler. In T20 they are rare and often lift required rate in a chase.",
      advanced:
        "Bowling figures treat wides and no-balls as conceded runs, so they prevent a maiden. PulseIQ does not currently expose a maiden boolean; you would derive it from consecutive legal deliveries with zero bowler-conceded runs.",
    },
  },
  {
    id: "strike-rate",
    title: "Strike rate",
    keywords: ["strike rate", "batting strike"],
    answers: {
      beginner:
        "Batting strike rate says how fast a batter scores. 100 means 100 runs per 100 balls faced.",
      casual:
        "Strike rate = runs ÷ balls faced × 100. T20 batters often sit well above 120; a falling strike rate in a chase can leave too much for the finish.",
      advanced:
        "Strike rate is a batter metric, not a team chase metric. PulseIQ match state tracks innings runs, legal balls and rates, not per-player strike rate in the explanation API.",
    },
  },
  {
    id: "economy",
    title: "Economy rate",
    keywords: ["economy", "economy rate", "bowling economy"],
    answers: {
      beginner:
        "Economy rate is how many runs a bowler gives away each over. Lower is better for the bowling team.",
      casual:
        "Economy = runs conceded ÷ overs bowled. In T20, around six an over is excellent; nine-plus is expensive unless wickets come with it.",
      advanced:
        "Economy uses bowler-conceded runs (including wides and no-balls, excluding byes/leg-byes depending on convention). The Phase 3 explanation API does not return bowler economy; this is general cricket knowledge.",
    },
  },
  {
    id: "no-ball",
    title: "No-ball",
    keywords: ["no-ball", "no ball", "noball", "free hit"],
    answers: {
      beginner:
        "A no-ball is an illegal delivery — often because the bowler overstepped. The batting team gets a run and usually a free hit next ball in T20 and ODI cricket.",
      casual:
        "Front-foot no-balls, over-waist full tosses and dangerous beamers are typical no-ball modes. The extra is scored, the ball is re-bowled, and limited-overs cricket awards a free hit.",
      advanced:
        "PulseIQ flags `is_noball` on reconstructed deliveries. Free-hit state is not a separate API field in this release. Do not assume a free hit unless the source delivery notes it.",
    },
  },
  {
    id: "wide",
    title: "Wide",
    keywords: ["wide ball", "wides", "wide delivery"],
    answers: {
      beginner:
        "A wide is a ball too far from the batter to hit fairly. The batting team gets a run and the ball is bowled again.",
      casual:
        "Wides add one extra (plus any runs taken) and do not count as a legal ball in the over. Down-leg wides are common in T20 as bowlers follow moving batters.",
      advanced:
        "Reconstructed deliveries expose `is_wide`. Wides increment extras and not legal-ball count. PulseIQ does not invent wide calls; they come from the Cricsheet delivery.",
    },
  },
  {
    id: "hat-trick",
    title: "Hat-trick",
    keywords: ["hat-trick", "hat trick", "three in three"],
    answers: {
      beginner:
        "A hat-trick is three wickets in three consecutive legal balls by the same bowler.",
      casual:
        "The three balls can span overs or even innings in some interpretations, but they must be consecutive legal deliveries by that bowler. It is rare in T20.",
      advanced:
        "PulseIQ does not currently emit a hat-trick detector. Claiming a hat-trick would require checking three consecutive counting wickets for one bowler in reconstructed deliveries — we do not auto-label that in this companion.",
    },
  },
  {
    id: "run-out",
    title: "Run out",
    keywords: ["run out", "run-out", "runout"],
    answers: {
      beginner:
        "A run out happens when a fielder hits the stumps with the ball while the batters are running and a batter is short of the crease.",
      casual:
        "Either batter can be run out. Direct hits and relay throws both count. A batter is safe if some part of the bat or body is grounded behind the popping crease.",
      advanced:
        "Cricsheet encodes run-outs in the wicket `kind`. PulseIQ copies that onto reconstructed deliveries. The companion will not invent a run out that is not in the source file.",
    },
  },
  {
    id: "catch",
    title: "Caught",
    keywords: ["caught", "catch", "skied"],
    answers: {
      beginner:
        "Caught means a fielder took the ball in the air after the batter hit it, before it bounced.",
      casual:
        "Caught behind, slip catches and outfield catches all dismiss the striker. A bump ball (hitting the ground first) is not out.",
      advanced:
        "Wicket kind `caught` or `caught and bowled` is source data. PulseIQ does not infer catch difficulty or fielder positioning beyond names in the Cricsheet wicket object.",
    },
  },
  {
    id: "stumping",
    title: "Stumping",
    keywords: ["stumping", "stumped", "keeper stumps"],
    answers: {
      beginner:
        "A stumping is when the wicketkeeper breaks the stumps while the batter is out of the crease, usually after missing the ball.",
      casual:
        "The batter must not be attempting a run (that would be a run out). Keepers often stump batters who leave the crease to spin.",
      advanced:
        "Cricsheet uses wicket kind `stumped`. PulseIQ copies it. This learning answer is not a claim about any specific sample delivery unless you ask in match mode with that state selected.",
    },
  },
  {
    id: "death-overs",
    title: "Death overs",
    keywords: ["death overs", "death over", "last overs", "slog overs"],
    answers: {
      beginner:
        "Death overs are the last few overs of an innings, when batting teams try to score very quickly and bowlers try to stop boundaries.",
      casual:
        "In T20 the death is often overs 16–20. Yorkers, slower balls and wide lines are common. Required rate in a chase is usually decided here.",
      advanced:
        "“Death overs” is commentary language, not an official phase in PulseIQ state. Use `balls_remaining` and `required_run_rate` from reconstructed chase state instead of inventing a death-over flag.",
    },
  },
  {
    id: "toss",
    title: "Toss",
    keywords: ["toss", "chose to bat", "chose to field"],
    answers: {
      beginner:
        "Before the match, captains flip a coin. The winner chooses to bat or to bowl first.",
      casual:
        "T20 captains often chase at night under lights, but that is a tactic, not a rule. PulseIQ shows toss winner and decision when the catalog includes them.",
      advanced:
        "Match detail exposes `toss_winner` and `toss_decision` from Cricsheet. If those fields are null, the companion will say they are not in the payload rather than guessing.",
    },
  },
  {
    id: "wickets-remaining",
    title: "Wickets remaining",
    keywords: [
      "wickets remaining",
      "wickets in hand",
      "chase strategy",
      "how do wickets remaining",
    ],
    answers: {
      beginner:
        "Wickets remaining are how many batters are still to come. More wickets usually means the team can take more risks while chasing.",
      casual:
        "Wickets in hand are batting resources. A side with six wickets left can hunt a high required rate; two wickets left usually means they must protect the innings and pick singles.",
      advanced:
        "Wickets remaining bound how aggressively a chase can be played. PulseIQ copies `wickets_remaining` from reconstructed state. The explainer does not estimate resources — if the field is missing, it stays unknown.",
    },
  },
  {
    id: "t20",
    title: "T20 cricket",
    keywords: ["t20", "twenty20", "twenty 20"],
    answers: {
      beginner:
        "T20 is a short cricket format. Each team usually bats for up to 20 overs. Games last about three hours.",
      casual:
        "T20 rewards strike rotation and boundary hitting. Fielding restrictions, free hits and a short innings create the momentum swings PulseIQ tries to explain on historical samples.",
      advanced:
        "PulseIQ’s current catalog is Cricsheet T20/IT20 samples. Chase win-probability is trained on a small completed-match set and is not a production-accurate live model.",
    },
  },
];

export function findKnowledgeTopic(question: string): KnowledgeTopic | null {
  const normalized = question.toLowerCase().replace(/[?!.,]/g, " ").replace(/\s+/g, " ").trim();
  if (!normalized) {
    return null;
  }
  let best: { topic: KnowledgeTopic; score: number } | null = null;
  for (const topic of CRICKET_KNOWLEDGE) {
    let score = 0;
    for (const keyword of topic.keywords) {
      if (normalized.includes(keyword)) {
        score = Math.max(score, keyword.length);
      }
    }
    if (score > 0 && (!best || score > best.score)) {
      best = { topic, score };
    }
  }
  return best && best.score >= 3 ? best.topic : null;
}

export function knowledgeAnswer(topic: KnowledgeTopic, level: AudienceLevel): string {
  return topic.answers[level];
}
