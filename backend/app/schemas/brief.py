from pydantic import BaseModel, Field


class BriefIn(BaseModel):
    """Structured fields are all optional — at minimum, raw_text must carry the content."""

    raw_text: str = Field(default="", description="Full free-text brief")

    brand: str | None = None
    product_name: str | None = None
    category: str | None = None
    concept: str | None = None
    benefit: str | None = None
    functional_claims: list[str] = Field(default_factory=list)
    emotional_claims: list[str] = Field(default_factory=list)
    packaging: str | None = None
    price: str | None = None
    pack_size: str | None = None
    target_consumers: str | None = None
    usage_occasions: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    launch_market: str | None = None
    competitors: list[str] = Field(default_factory=list)
    media_plan: str | None = None
    sampling_plan: str | None = None
    promotion_plan: str | None = None
    known_risks: list[str] = Field(default_factory=list)


class BriefOut(BaseModel):
    brief_id: str
    stored: bool
    field_count: int
