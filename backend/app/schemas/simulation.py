from pydantic import BaseModel, Field


class SimulationRunIn(BaseModel):
    rounds: int = Field(default=6, ge=1, le=6)
    deterministic: bool = True
    seed: int = 42
    include_market_actors: bool = True
    force_rerun: bool = True
    temperature: float = Field(default=0.2, ge=0.0, le=1.5)


class RoundSummary(BaseModel):
    round_number: int
    stage_name: str
    consumer_events: int
    market_actor_events: int
    action_distribution: dict[str, int]
    avg_sentiment: float
    avg_trial_probability: float


class SimulationRunOut(BaseModel):
    simulation_status: str
    source_mode: str
    rounds_run: int
    total_events: int
    consumer_events: int
    market_actor_events: int
    action_distribution: dict[str, int]
    segment_summary: dict[str, dict]
    top_barriers: list[tuple[str, int]] = Field(default_factory=list)
    top_triggers: list[tuple[str, int]] = Field(default_factory=list)
    per_round: list[RoundSummary] = Field(default_factory=list)
    token_usage: dict | None = None


class EventsSummaryOut(BaseModel):
    total_events: int
    consumer_events: int
    market_actor_events: int
    rounds_run: int
    action_distribution: dict[str, int]
    per_round: list[RoundSummary] = Field(default_factory=list)
    segment_summary: dict[str, dict]
    top_barriers: list[tuple[str, int]] = Field(default_factory=list)
    top_triggers: list[tuple[str, int]] = Field(default_factory=list)


class QuestionIn(BaseModel):
    question: str
    interview_agents: list[str] = Field(default_factory=list)
    max_evidence: int = 10


class QuestionOut(BaseModel):
    answer: str
    evidence_event_ids: list[str] = Field(default_factory=list)
