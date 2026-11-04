"use client";

import { useMemo, useState } from "react";

import { formatProbability } from "@/lib/format";
import { useLiveIntelligence } from "@/hooks/useLiveIntelligence";
import type { ProbabilityPredictionView } from "@/types/api";

const WIDTH = 800;
const HEIGHT = 280;
const PAD = { top: 24, right: 16, bottom: 36, left: 44 };

export function WinProbabilityChart() {
  const {
    predictions,
    winAvailable,
    winReason,
    winModel,
    sequence,
    sequences,
    selectGraphSequence,
    predictionAtSequence,
    moments,
  } = useLiveIntelligence();
  const [hover, setHover] = useState<ProbabilityPredictionView | null>(null);
  const [open, setOpen] = useState(true);

  const maxSequence = sequences[sequences.length - 1] ?? 0;
  const paths = useMemo(
    () => lineSegments(predictions, maxSequence),
    [predictions, maxSequence],
  );
  const momentMarks = useMemo(
    () =>
      moments.filter((moment) =>
        predictions.some((item) => item.sequence === moment.sequence),
      ),
    [moments, predictions],
  );

  return (
    <section className="rounded-[28px] border border-white/10 bg-[var(--ink-2)] p-4 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[var(--gold)]">
            Win probability intelligence
          </p>
          <h3 className="mt-1 font-display text-2xl uppercase">Chase model series</h3>
        </div>
        <button
          type="button"
          className="text-sm text-white/60 xl:hidden"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Hide chart" : "Show chart"}
        </button>
      </div>
      {predictionAtSequence ? (
        <p className="mt-3 rounded-full border border-white/15 px-3 py-1 text-sm inline-block">
          Seq {predictionAtSequence.sequence}:{" "}
          {formatProbability(predictionAtSequence.probability)}
        </p>
      ) : (
        <p className="mt-3 text-sm text-muted">No prediction at this sequence</p>
      )}

      <div className={open ? "block" : "hidden xl:block"}>
      {!winAvailable || predictions.length === 0 ? (
        <p className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 text-sm text-white/75" role="status">
          {winReason === "model_artifact_missing"
            ? "The win-probability model artifact is not loaded. PulseIQ will not invent a curve."
            : winReason === "unsupported_state"
              ? "This reconstructed state is outside the model’s supported chase window."
              : winReason ??
                "No supported probability points are available for this historical match."}
        </p>
      ) : (
        <div className="relative mt-4">
          <svg
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            className="h-auto w-full"
            role="img"
            aria-label="Historical chase win probability by delivery sequence"
          >
            <line
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={HEIGHT - PAD.bottom}
              y2={HEIGHT - PAD.bottom}
              stroke="rgba(255,255,255,0.18)"
            />
            <line
              x1={PAD.left}
              x2={PAD.left}
              y1={PAD.top}
              y2={HEIGHT - PAD.bottom}
              stroke="rgba(255,255,255,0.18)"
            />
            {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
              const y = yFor(tick);
              return (
                <g key={tick}>
                  <line
                    x1={PAD.left}
                    x2={WIDTH - PAD.right}
                    y1={y}
                    y2={y}
                    stroke="rgba(255,255,255,0.06)"
                  />
                  <text
                    x={PAD.left - 8}
                    y={y + 4}
                    textAnchor="end"
                    fill="#9aa3b5"
                    fontSize="11"
                  >
                    {Math.round(tick * 100)}%
                  </text>
                </g>
              );
            })}
            {paths.map((path, index) => (
              <path
                key={index}
                d={path}
                fill="none"
                stroke="var(--electric)"
                strokeWidth="2.5"
              />
            ))}
            <line
              x1={xFor(sequence, maxSequence)}
              x2={xFor(sequence, maxSequence)}
              y1={PAD.top}
              y2={HEIGHT - PAD.bottom}
              stroke="var(--red)"
              strokeDasharray="4 4"
            />
            {momentMarks.map((moment) => (
              <circle
                key={`m-${moment.sequence}`}
                cx={xFor(moment.sequence, maxSequence)}
                cy={yFor(
                  predictions.find((item) => item.sequence === moment.sequence)
                    ?.probability ?? 0,
                )}
                r="4"
                fill="var(--gold)"
              />
            ))}
            {predictions.map((item) => (
              <circle
                key={item.sequence}
                cx={xFor(item.sequence, maxSequence)}
                cy={yFor(item.probability)}
                r={item.sequence === sequence ? 5 : 3}
                fill={item.sequence === sequence ? "var(--red)" : "white"}
                className="cursor-pointer"
                onMouseEnter={() => setHover(item)}
                onMouseLeave={() => setHover(null)}
                onClick={() => selectGraphSequence(item.sequence)}
              />
            ))}
            <text
              x={WIDTH / 2}
              y={HEIGHT - 8}
              textAnchor="middle"
              fill="#9aa3b5"
              fontSize="11"
            >
              Delivery sequence
            </text>
          </svg>
          {hover ? (
            <div className="pointer-events-none absolute top-2 right-2 rounded-xl border border-white/15 bg-black/80 px-3 py-2 text-xs">
              Seq {hover.sequence}: {formatProbability(hover.probability)}
            </div>
          ) : null}
        </div>
      )}

      {winModel ? (
        <div className="mt-4 space-y-1 text-xs text-muted">
          <p>
            Model {winModel.model_id} · {winModel.model_kind} · schema{" "}
            {winModel.feature_schema_version}
            {winModel.fitted_split ? ` · fitted on ${winModel.fitted_split}` : ""}
          </p>
          <p>
            Training rows {winModel.n_train_rows}
            {winModel.validation_role ? ` · ${winModel.validation_role}` : ""}
          </p>
          {winModel.evaluation_is_meaningful === false ? (
            <p className="text-[var(--gold)]" role="note">
              These probability estimates are experimental and not production-validated.
              {winModel.evaluation_limitation
                ? ` ${winModel.evaluation_limitation}`
                : ""}
            </p>
          ) : winModel.evaluation_limitation ? (
            <p>{winModel.evaluation_limitation}</p>
          ) : null}
        </div>
      ) : null}
      <p className="mt-3 text-[11px] text-muted">
        Historical Cricsheet reconstruction. Predictions are not guaranteed outcomes.
      </p>
      </div>
    </section>
  );
}

function xFor(sequence: number, maxSequence: number): number {
  const inner = WIDTH - PAD.left - PAD.right;
  if (maxSequence <= 0) {
    return PAD.left;
  }
  return PAD.left + (sequence / maxSequence) * inner;
}

function yFor(probability: number): number {
  const inner = HEIGHT - PAD.top - PAD.bottom;
  return PAD.top + (1 - probability) * inner;
}

function lineSegments(
  predictions: ProbabilityPredictionView[],
  maxSequence: number,
): string[] {
  const ordered = [...predictions].sort((a, b) => a.sequence - b.sequence);
  const segments: string[] = [];
  let current: string[] = [];
  let previous: number | null = null;
  for (const point of ordered) {
    const command = `${current.length === 0 ? "M" : "L"} ${xFor(point.sequence, maxSequence).toFixed(1)} ${yFor(point.probability).toFixed(1)}`;
    if (previous != null && point.sequence > previous + 1) {
      if (current.length > 1) {
        segments.push(current.join(" "));
      }
      current = [`M ${xFor(point.sequence, maxSequence).toFixed(1)} ${yFor(point.probability).toFixed(1)}`];
    } else {
      current.push(command);
    }
    previous = point.sequence;
  }
  if (current.length > 1) {
    segments.push(current.join(" "));
  }
  return segments;
}
