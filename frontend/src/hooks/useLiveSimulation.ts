import { useCallback, useEffect, useRef, useState } from "react";
import { startLiveSimulation, streamUrl } from "../api/liveSimulation";
import type { LiveProgress, LiveStartIn, LiveStreamMessage } from "../types/api";

export type LiveStatus = "idle" | "starting" | "streaming" | "completed" | "failed" | "disconnected";

const TRIAL = new Set(["purchase_trial"]);
const REPEAT = new Set(["repeat_purchase_intent", "repeat_purchase"]);
const RECOMMEND = new Set(["recommend", "share_with_friend"]);
const COMPLAINT = new Set(["complain", "comment_negative"]);

const STREAM_EVENT_TYPES = [
  "run_started", "round_started", "agent_started", "event_generated",
  "agent_memory_updated", "market_actor_event_generated", "round_completed",
  "run_completed", "run_failed", "heartbeat",
];

export interface LiveMetrics {
  trial: number;
  repeat: number;
  recommend: number;
  complaint: number;
  sentSum: number;
  sentN: number;
}

const EMPTY_METRICS: LiveMetrics = { trial: 0, repeat: 0, recommend: 0, complaint: 0, sentSum: 0, sentN: 0 };

export function useLiveSimulation(projectId: string) {
  const [status, setStatus] = useState<LiveStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<LiveProgress | null>(null);
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);
  const [currentRound, setCurrentRound] = useState<number | null>(null);
  const [events, setEvents] = useState<LiveStreamMessage["payload"][]>([]);
  const [metrics, setMetrics] = useState<LiveMetrics>(EMPTY_METRICS);
  const [runId, setRunId] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const close = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    close();
    setStatus("idle");
    setError(null);
    setProgress(null);
    setActiveAgentId(null);
    setCurrentRound(null);
    setEvents([]);
    setMetrics(EMPTY_METRICS);
    setRunId(null);
  }, [close]);

  const handle = useCallback((m: LiveStreamMessage) => {
    if (m.progress) setProgress(m.progress);
    if (m.round_number) setCurrentRound(m.round_number);
    switch (m.type) {
      case "agent_started":
        setActiveAgentId(m.payload.agent_id ?? null);
        break;
      case "event_generated":
        setActiveAgentId(m.payload.agent_id ?? null);
        setEvents((prev) => [m.payload, ...prev].slice(0, 200));
        setMetrics((c) => {
          const a = m.payload.action_type;
          const s = typeof m.payload.sentiment_score === "number" ? m.payload.sentiment_score : null;
          return {
            trial: c.trial + (TRIAL.has(a) ? 1 : 0),
            repeat: c.repeat + (REPEAT.has(a) ? 1 : 0),
            recommend: c.recommend + (RECOMMEND.has(a) ? 1 : 0),
            complaint: c.complaint + (COMPLAINT.has(a) ? 1 : 0),
            sentSum: c.sentSum + (s ?? 0),
            sentN: c.sentN + (s !== null ? 1 : 0),
          };
        });
        break;
      case "run_completed":
        setStatus("completed");
        setActiveAgentId(null);
        close();
        break;
      case "run_failed":
        setStatus("failed");
        setError(m.payload?.error ?? "run_failed");
        close();
        break;
    }
  }, [close]);

  const start = useCallback(async (params: LiveStartIn) => {
    reset();
    setStatus("starting");
    try {
      const out = await startLiveSimulation(projectId, params);
      setRunId(out.run_id);
      const es = new EventSource(streamUrl(projectId, out.run_id));
      esRef.current = es;
      setStatus("streaming");
      const onMsg = (e: MessageEvent) => {
        try {
          handle(JSON.parse(e.data) as LiveStreamMessage);
        } catch {
          /* ignore non-JSON (heartbeat comments) */
        }
      };
      STREAM_EVENT_TYPES.forEach((t) => es.addEventListener(t, onMsg as EventListener));
      es.addEventListener("message", onMsg as EventListener);
      es.onerror = () => {
        // browser closes/reconnects on error; if not completed, surface a disconnect
        setStatus((s) => (s === "completed" ? s : "disconnected"));
        close();
      };
    } catch (e) {
      setStatus("failed");
      setError(e instanceof Error ? e.message : "Failed to start live simulation");
    }
  }, [projectId, reset, handle, close]);

  useEffect(() => () => close(), [close]);

  return { status, error, progress, activeAgentId, currentRound, events, metrics, runId, start, reset };
}
