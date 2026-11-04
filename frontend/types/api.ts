export type DataSource = "historical_cricsheet";

export type AudienceLevel = "beginner" | "casual" | "advanced";

export type OutcomeInfo = {
  winner: string | null;
  result: string | null;
  win_by_runs: number | null;
  win_by_wickets: number | null;
  win_by_innings: number | null;
  method: string | null;
  eliminator: string | null;
  bowl_out_winner: string | null;
};

export type MatchSummary = {
  source_match_id: string;
  data_source: DataSource;
  teams: string[];
  dates: string[];
  venue: string | null;
  city: string | null;
  match_type: string;
  gender: string;
  season: string;
  event_name: string | null;
  outcome: OutcomeInfo;
  innings_count: number;
  delivery_count: number;
  is_historical: boolean;
};

export type MatchDetail = MatchSummary & {
  balls_per_over: number;
  scheduled_overs: number | null;
  toss_winner: string | null;
  toss_decision: string | null;
  player_of_match: string[];
  latest_sequence: number;
};

export type MatchListResponse = {
  data_source: DataSource;
  count: number;
  matches: MatchSummary[];
};

export type DeliveryApplied = {
  sequence: number;
  actual_delivery: string | null;
  batter: string;
  bowler: string;
  non_striker: string;
  batter_runs: number;
  extras_runs: number;
  total_runs: number;
  is_legal_delivery: boolean;
  is_wide: boolean;
  is_noball: boolean;
  non_boundary: boolean;
  wickets: Array<{
    kind: string;
    player_out: string;
    counts_as_wicket: boolean;
  }>;
};

export type MatchState = {
  source_match_id: string;
  sequence: number;
  innings_number: number | null;
  innings_phase: string | null;
  is_super_over: boolean;
  batting_team: string | null;
  bowling_team: string | null;
  innings_runs: number;
  innings_wickets: number;
  overs: string;
  current_run_rate: number | null;
  balls_remaining: number | null;
  target: number | null;
  runs_remaining: number | null;
  required_run_rate: number | null;
  wickets_remaining: number | null;
  last_delivery: DeliveryApplied | null;
  innings_complete: boolean;
  match_complete: boolean;
  is_active_prediction_state: boolean;
  outcome: OutcomeInfo;
};

export type MatchStateResponse = {
  source_match_id: string;
  data_source: DataSource;
  requested_sequence: number | null;
  latest_sequence: number;
  state: MatchState;
};

export type ModelMetadataView = {
  model_id: string;
  model_kind: string;
  feature_schema_version: string;
  evaluation_is_meaningful: boolean;
  evaluation_limitation: string | null;
  trained_at: string;
  n_train_rows: number;
  notes: string[];
};

export type ProbabilityPredictionView = {
  source_match_id: string;
  sequence: number;
  probability: number;
  model_id: string;
  feature_schema_version: string;
};

export type WinProbabilityResponse = {
  source_match_id: string;
  data_source: DataSource;
  available: boolean;
  unavailable_reason: string | null;
  requested_sequence: number | null;
  predictions: ProbabilityPredictionView[];
  model: ModelMetadataView | null;
};

export type MomentView = {
  moment_type: string;
  source_match_id: string;
  sequence: number;
  probability_before: number;
  probability_after: number;
  probability_change: number;
  reasons: string[];
  match_context: Record<string, unknown>;
};

export type MomentsResponse = {
  source_match_id: string;
  data_source: DataSource;
  available: boolean;
  unavailable_reason: string | null;
  count: number;
  moments: MomentView[];
  model: ModelMetadataView | null;
};

export type ExplanationResponse = {
  summary: string;
  what_happened: string;
  why_it_matters: string;
  match_context: string;
  key_factors: string[];
  audience_level: AudienceLevel;
  source_match_id: string;
  source_sequence: number;
  generated_at: string;
  model_provider: string;
  model_name: string;
  data_source: DataSource;
  grounded: boolean;
};

export type ApiErrorBody = {
  error: string;
  code: string;
  detail: string | null;
};
