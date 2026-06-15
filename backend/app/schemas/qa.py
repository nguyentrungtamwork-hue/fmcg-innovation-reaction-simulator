"""Deep Q&A schemas (Phase 7)."""
from pydantic import BaseModel, Field


class QAEvidenceRef(BaseModel):
    event_id: str
    round_number: int
    agent_id: str
    segment_name: str | None = None
    action_type: str
    short_reaction_excerpt: str


class InterviewAnswer(BaseModel):
    agent_id: str
    segment_name: str | None = None
    persona_label: str
    answer: str
    evidence_from_agent_memory: list[str] = Field(default_factory=list)


class QAAnswer(BaseModel):
    direct_answer: str
    evidence_summary: str
    supporting_events: list[QAEvidenceRef] = Field(default_factory=list)
    supporting_segments: list[str] = Field(default_factory=list)
    confidence_score: float
    limitations: list[str] = Field(default_factory=list)
    recommended_next_action: list[str] = Field(default_factory=list)
    # populated only for interview-style questions
    selected_agents: list[str] = Field(default_factory=list)
    simulated_interview_answers: list[InterviewAnswer] = Field(default_factory=list)


class QuestionIn(BaseModel):
    question: str
    use_llm: bool = False
    include_evidence: bool = True
    max_evidence_events: int = 5


class QuestionOut(BaseModel):
    project_id: str
    question: str
    intent: str
    answer: QAAnswer
    source_mode: str = "deterministic"
