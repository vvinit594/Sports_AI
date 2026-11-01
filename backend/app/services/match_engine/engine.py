"""Reconstruct deterministic ball-by-ball cricket match state."""

from __future__ import annotations

from app.core.cricket_rules import (
    balls_to_overs_notation,
    current_run_rate,
    innings_is_all_out,
    is_known_dismissal_kind,
    max_wickets_available,
    required_run_rate,
    scheduled_balls_exhausted,
    scheduled_balls_for_innings,
    target_reached,
)
from app.core.exceptions import MatchEngineError
from app.schemas.enums import (
    InningsCompletionReason,
    InningsPhase,
    KnowledgeHorizon,
    MatchCompletionReason,
    TargetSource,
)
from app.schemas.match import NormalizedDelivery, NormalizedInnings, NormalizedMatch
from app.schemas.state import DeliveryApplied, MatchState


class MatchStateEngine:
    """Walk a normalized match and produce a state after every delivery."""

    def __init__(self, match: NormalizedMatch):
        self.match = match

    def initial_state(self) -> MatchState:
        if not self.match.innings:
            return self._empty_match_state()
        return self._new_innings_state(
            self.match.innings[0],
            sequence=0,
            completed_totals={},
        )

    def reconstruct(self) -> list[MatchState]:
        """Return states including the pre-match snapshot at sequence 0."""

        if not self.match.innings:
            return [self._empty_match_state()]

        states: list[MatchState] = []
        current = self.initial_state()
        states.append(current)
        completed_totals: dict[int, int] = {}

        for innings in self.match.innings:
            if innings.innings_number != (current.innings_number or 1):
                already_complete = current.match_complete
                already_reason = current.match_completion_reason
                current = self._new_innings_state(
                    innings,
                    sequence=current.sequence,
                    completed_totals=completed_totals,
                )
                if already_complete:
                    current = current.model_copy(
                        update={
                            "match_complete": True,
                            "match_completion_reason": already_reason,
                            "is_active_prediction_state": False,
                        }
                    )

            if not innings.deliveries:
                reason = self._empty_innings_reason(innings)
                current = self._mark_innings_complete(current, innings, reason, just_completed=True)
                current = self._apply_post_innings_knowledge(current, innings)
                current = self._maybe_complete_match(
                    current,
                    innings,
                    reason,
                    is_last_source_delivery=True,
                )
                if current not in states:
                    states.append(current)
                completed_totals[innings.innings_number] = current.innings_runs
                continue

            innings_already_complete = False
            completion_reason: InningsCompletionReason | None = None
            for index, delivery in enumerate(innings.deliveries):
                is_last = index == len(innings.deliveries) - 1
                current = self._apply_delivery(current, innings, delivery)
                if innings_already_complete:
                    current = current.model_copy(
                        update={
                            "source_delivery_after_terminal": True,
                            "is_active_prediction_state": False,
                            "innings_complete": True,
                            "innings_just_completed": False,
                            "innings_completion_reason": completion_reason,
                            "match_complete": current.match_complete,
                            "match_completion_reason": current.match_completion_reason,
                        }
                    )
                else:
                    reason = self._cricket_terminal_reason(current, innings)
                    if reason is not None:
                        innings_already_complete = True
                        completion_reason = reason
                        current = self._mark_innings_complete(
                            current,
                            innings,
                            reason,
                            just_completed=True,
                        )
                        current = self._maybe_complete_match(
                            current,
                            innings,
                            reason,
                            is_last_source_delivery=is_last,
                        )

                if is_last:
                    if not innings_already_complete:
                        completion_reason = InningsCompletionReason.SOURCE_ENDED
                        current = self._mark_innings_complete(
                            current,
                            innings,
                            completion_reason,
                            just_completed=True,
                        )
                        current = self._maybe_complete_match(
                            current,
                            innings,
                            completion_reason,
                            is_last_source_delivery=True,
                        )
                    current = self._apply_post_innings_knowledge(current, innings)
                    if innings.innings_number == len(self.match.innings):
                        current = current.model_copy(update={"source_record_complete": True})

                states.append(current)

            completed_totals[innings.innings_number] = current.innings_runs

        return states

    def apply_until(self, sequence: int) -> MatchState:
        if sequence < 0:
            raise MatchEngineError("sequence cannot be negative")
        states = self.reconstruct()
        for state in reversed(states):
            if state.sequence == sequence:
                return state
        raise MatchEngineError(f"no match state at sequence {sequence}")

    def _apply_delivery(
        self,
        state: MatchState,
        innings: NormalizedInnings,
        delivery: NormalizedDelivery,
    ) -> MatchState:
        if delivery.innings_number != innings.innings_number:
            raise MatchEngineError("delivery innings does not match current innings")

        warnings = list(state.warnings)
        innings_runs = state.innings_runs_at_delivery + delivery.total_runs
        legal_balls = state.legal_balls + (1 if delivery.is_legal_delivery else 0)
        total_deliveries = state.total_deliveries + 1
        wicket_events = state.innings_wicket_events + len(delivery.wickets)
        wickets = state.innings_wickets
        for wicket in delivery.wickets:
            if wicket.counts_as_wicket:
                wickets += 1
            if not is_known_dismissal_kind(wicket.kind):
                warnings.append(
                    f"unknown dismissal kind '{wicket.kind}' on sequence {delivery.sequence}"
                )

        return self._build_state(
            innings=innings,
            sequence=delivery.sequence,
            innings_runs=innings_runs,
            innings_runs_at_delivery=innings_runs,
            innings_wickets=wickets,
            innings_wicket_events=wicket_events,
            legal_balls=legal_balls,
            total_deliveries=total_deliveries,
            last_delivery=DeliveryApplied(
                sequence=delivery.sequence,
                actual_delivery=delivery.actual_delivery,
                batter=delivery.batter,
                bowler=delivery.bowler,
                non_striker=delivery.non_striker,
                batter_runs=delivery.batter_runs,
                extras_runs=delivery.extras_runs,
                total_runs=delivery.total_runs,
                is_legal_delivery=delivery.is_legal_delivery,
                is_wide=delivery.is_wide,
                is_noball=delivery.is_noball,
                wickets=delivery.wickets,
            ),
            warnings=tuple(warnings),
            knowledge_horizon=KnowledgeHorizon.AT_DELIVERY,
            includes_post_innings_penalty=False,
            innings_complete=False,
            innings_just_completed=False,
            innings_completion_reason=None,
            match_complete=state.match_complete,
            match_completion_reason=state.match_completion_reason,
            is_active_prediction_state=not state.match_complete,
            source_record_complete=False,
            source_delivery_after_terminal=False,
            target=state.target,
            target_source=state.target_source,
            scheduled_balls=state.scheduled_balls,
        )

    def _new_innings_state(
        self,
        innings: NormalizedInnings,
        *,
        sequence: int,
        completed_totals: dict[int, int],
    ) -> MatchState:
        target, target_source = self._resolve_target(innings, completed_totals)
        scheduled_balls = scheduled_balls_for_innings(
            target_overs=innings.target.overs if innings.target else None,
            is_super_over=innings.is_super_over,
            match_overs=self.match.info.scheduled_overs,
            match_type=self.match.info.match_type,
            balls_per_over=self.match.info.balls_per_over,
        )
        opening_runs = innings.penalty_runs.pre
        return self._build_state(
            innings=innings,
            sequence=sequence,
            innings_runs=opening_runs,
            innings_runs_at_delivery=opening_runs,
            innings_wickets=0,
            innings_wicket_events=0,
            legal_balls=0,
            total_deliveries=0,
            last_delivery=None,
            warnings=(),
            knowledge_horizon=KnowledgeHorizon.PRE_INNINGS,
            includes_post_innings_penalty=False,
            innings_complete=False,
            innings_just_completed=False,
            innings_completion_reason=None,
            match_complete=False,
            match_completion_reason=None,
            is_active_prediction_state=True,
            source_record_complete=False,
            source_delivery_after_terminal=False,
            target=target,
            target_source=target_source,
            scheduled_balls=scheduled_balls,
        )

    def _cricket_terminal_reason(
        self,
        state: MatchState,
        innings: NormalizedInnings,
    ) -> InningsCompletionReason | None:
        if innings.forfeited:
            return InningsCompletionReason.FORFEITED
        if innings.declared:
            return InningsCompletionReason.DECLARED
        if target_reached(state.innings_runs_at_delivery, state.target):
            return InningsCompletionReason.TARGET_REACHED
        if innings_is_all_out(state.innings_wickets, len(innings.absent_hurt)):
            return InningsCompletionReason.ALL_OUT
        if scheduled_balls_exhausted(state.legal_balls, state.scheduled_balls):
            return InningsCompletionReason.OVERS_EXHAUSTED
        return None

    def _empty_innings_reason(self, innings: NormalizedInnings) -> InningsCompletionReason:
        if innings.forfeited:
            return InningsCompletionReason.FORFEITED
        if innings.declared:
            return InningsCompletionReason.DECLARED
        return InningsCompletionReason.SOURCE_ENDED

    def _mark_innings_complete(
        self,
        state: MatchState,
        innings: NormalizedInnings,
        reason: InningsCompletionReason,
        *,
        just_completed: bool,
    ) -> MatchState:
        return state.model_copy(
            update={
                "innings_complete": True,
                "innings_just_completed": just_completed,
                "innings_completion_reason": reason,
                "is_active_prediction_state": False,
            }
        )

    def _maybe_complete_match(
        self,
        state: MatchState,
        innings: NormalizedInnings,
        reason: InningsCompletionReason,
        *,
        is_last_source_delivery: bool,
    ) -> MatchState:
        is_last_innings = innings.innings_number == len(self.match.innings)
        match_reason: MatchCompletionReason | None = None
        if reason == InningsCompletionReason.TARGET_REACHED:
            match_reason = MatchCompletionReason.TARGET_REACHED
        elif is_last_innings and reason in {
            InningsCompletionReason.ALL_OUT,
            InningsCompletionReason.OVERS_EXHAUSTED,
            InningsCompletionReason.DECLARED,
            InningsCompletionReason.FORFEITED,
        }:
            match_reason = MatchCompletionReason.LAST_INNINGS_COMPLETE
        elif is_last_innings and is_last_source_delivery:
            match_reason = MatchCompletionReason.SOURCE_ENDED

        if match_reason is None:
            return state
        return state.model_copy(
            update={
                "match_complete": True,
                "match_completion_reason": match_reason,
                "is_active_prediction_state": False,
            }
        )

    def _apply_post_innings_knowledge(
        self,
        state: MatchState,
        innings: NormalizedInnings,
    ) -> MatchState:
        innings_runs = state.innings_runs_at_delivery + innings.penalty_runs.post
        return state.model_copy(
            update={
                "innings_runs": innings_runs,
                "current_run_rate": current_run_rate(
                    innings_runs,
                    state.legal_balls,
                    self.match.info.balls_per_over,
                ),
                "runs_remaining": None if state.target is None else state.target - innings_runs,
                "required_run_rate": required_run_rate(
                    None if state.target is None else state.target - innings_runs,
                    state.balls_remaining,
                    self.match.info.balls_per_over,
                ),
                "includes_post_innings_penalty": True,
                "knowledge_horizon": KnowledgeHorizon.AFTER_INNINGS,
                "innings_complete": True,
            }
        )

    def _resolve_target(
        self,
        innings: NormalizedInnings,
        completed_totals: dict[int, int],
    ) -> tuple[int | None, TargetSource]:
        if innings.target and innings.target.runs is not None:
            return innings.target.runs, TargetSource.CRICSHEET

        if innings.is_super_over:
            previous = self._previous_innings(innings.innings_number)
            if (
                previous
                and previous.is_super_over
                and previous.batting_team != innings.batting_team
                and previous.innings_number in completed_totals
            ):
                return completed_totals[previous.innings_number] + 1, TargetSource.DERIVED_PREVIOUS_INNINGS

        return None, TargetSource.NONE

    def _previous_innings(self, innings_number: int) -> NormalizedInnings | None:
        if innings_number <= 1:
            return None
        return self.match.innings_by_number(innings_number - 1)

    def _build_state(
        self,
        *,
        innings: NormalizedInnings,
        sequence: int,
        innings_runs: int,
        innings_runs_at_delivery: int,
        innings_wickets: int,
        innings_wicket_events: int,
        legal_balls: int,
        total_deliveries: int,
        last_delivery: DeliveryApplied | None,
        warnings: tuple[str, ...],
        knowledge_horizon: KnowledgeHorizon,
        includes_post_innings_penalty: bool,
        innings_complete: bool,
        innings_just_completed: bool,
        innings_completion_reason: InningsCompletionReason | None,
        match_complete: bool,
        match_completion_reason: MatchCompletionReason | None,
        is_active_prediction_state: bool,
        source_record_complete: bool,
        source_delivery_after_terminal: bool,
        target: int | None,
        target_source: TargetSource,
        scheduled_balls: int | None,
    ) -> MatchState:
        balls_remaining = None if scheduled_balls is None else max(0, scheduled_balls - legal_balls)
        runs_remaining = None if target is None else target - innings_runs
        max_wickets = max_wickets_available(len(innings.absent_hurt))
        return MatchState(
            source_match_id=self.match.source_match_id,
            sequence=sequence,
            innings_number=innings.innings_number,
            innings_phase=InningsPhase.SUPER_OVER if innings.is_super_over else InningsPhase.REGULATION,
            is_super_over=innings.is_super_over,
            batting_team=innings.batting_team,
            bowling_team=innings.bowling_team,
            innings_runs=innings_runs,
            innings_wickets=innings_wickets,
            innings_wicket_events=innings_wicket_events,
            legal_balls=legal_balls,
            total_deliveries=total_deliveries,
            overs=balls_to_overs_notation(legal_balls, self.match.info.balls_per_over),
            current_run_rate=current_run_rate(
                innings_runs,
                legal_balls,
                self.match.info.balls_per_over,
            ),
            scheduled_balls=scheduled_balls,
            balls_remaining=balls_remaining,
            target=target,
            target_source=target_source,
            runs_remaining=runs_remaining,
            required_run_rate=required_run_rate(
                runs_remaining,
                balls_remaining,
                self.match.info.balls_per_over,
            ),
            wickets_remaining=max(0, max_wickets - innings_wickets),
            last_delivery=last_delivery,
            innings_complete=innings_complete,
            innings_just_completed=innings_just_completed,
            innings_completion_reason=innings_completion_reason,
            match_complete=match_complete,
            match_completion_reason=match_completion_reason,
            is_active_prediction_state=is_active_prediction_state,
            source_record_complete=source_record_complete,
            source_delivery_after_terminal=source_delivery_after_terminal,
            knowledge_horizon=knowledge_horizon,
            includes_pre_innings_penalty=True,
            includes_post_innings_penalty=includes_post_innings_penalty,
            innings_runs_at_delivery=innings_runs_at_delivery,
            outcome=self.match.info.outcome,
            warnings=warnings,
        )

    def _empty_match_state(self) -> MatchState:
        return MatchState(
            source_match_id=self.match.source_match_id,
            sequence=0,
            innings_number=None,
            innings_phase=None,
            is_super_over=False,
            batting_team=None,
            bowling_team=None,
            innings_runs=0,
            innings_wickets=0,
            innings_wicket_events=0,
            legal_balls=0,
            total_deliveries=0,
            overs="0.0",
            current_run_rate=None,
            scheduled_balls=None,
            balls_remaining=None,
            target=None,
            target_source=TargetSource.NONE,
            runs_remaining=None,
            required_run_rate=None,
            wickets_remaining=None,
            last_delivery=None,
            innings_complete=True,
            innings_just_completed=False,
            innings_completion_reason=InningsCompletionReason.SOURCE_ENDED,
            match_complete=True,
            match_completion_reason=MatchCompletionReason.NO_INNINGS,
            is_active_prediction_state=False,
            source_record_complete=True,
            source_delivery_after_terminal=False,
            knowledge_horizon=KnowledgeHorizon.AFTER_INNINGS,
            includes_pre_innings_penalty=False,
            includes_post_innings_penalty=False,
            innings_runs_at_delivery=0,
            outcome=self.match.info.outcome,
            warnings=("match contains no innings",),
        )
