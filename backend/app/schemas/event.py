from datetime import datetime

from pydantic import BaseModel


class EventOut(BaseModel):
    id: str
    round_number: int
    stage_name: str
    agent_id: str
    agent_type: str
    segment_name: str | None = None
    touchpoint: str | None = None
    action_type: str
    content_seen: str | None = None
    reasoning: str | None = None
    generated_reaction: str | None = None
    emotional_tone: str | None = None
    confidence_score: float | None = None
    sentiment_score: float | None = None
    trial_probability: float | None = None
    purchase_intent_score: float | None = None
    repeat_probability: float | None = None
    trust_change: float | None = None
    barrier_detected: str | None = None
    trigger_detected: str | None = None
    scores: dict | None = None
    timestamp: datetime
