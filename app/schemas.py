"""Public normalized contract. Provider response bodies remain private."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Evidence(StrictModel):
    id: str
    field: Literal["headline", "summary", "full_text"]
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str


class Assessment(StrictModel):
    supplier_id: str
    p_link: float = Field(ge=0, le=1)
    p_identity: float | None = Field(default=None, ge=0, le=1)
    p_exposure: float | None = Field(default=None, ge=0, le=1)
    p_risk: float = Field(ge=0, le=1)
    p_urgent: float = Field(ge=0, le=1)
    is_risk: Literal["Y", "N"]
    urgent: Literal["Y", "N"]
    severity: float | None = Field(ge=1, le=10)
    severity_confidence: float | None = Field(default=None, ge=0, le=1)
    priority: float | None = Field(ge=0, le=100)
    priority_band: Literal["low", "medium", "high", "critical"] | None
    impact_status: Literal[
        "active", "monitoring", "resolved", "positive", "unrelated", "unclear"
    ]
    needs_review: bool
    review_reasons: list[str]
    evidence_ids: list[str]
    duration_days: float | None = Field(default=None, gt=0)
    duration_is_lower_bound: bool = False
    factor_values: dict[Literal["C", "U", "B", "G"], float]
    policy_version: str

    @model_validator(mode="after")
    def consistency(self):
        if self.is_risk == "N" and (
            self.urgent != "N" or self.priority not in (0, None)
        ):
            raise ValueError("No riesgo implica urgencia N y prioridad cero")
        if any(not 0 <= v <= 1 for v in self.factor_values.values()):
            raise ValueError("Factor fuera de rango")
        return self


class SourceReading(StrictModel):
    status: Literal["summary_only", "partial", "public_text"]
    checked_at: str | None = None
    source_url: str | None = None
    text_hash: str | None = None
    characters: int | None = None
    http_status: int | None = None
    reason: str | None = None
    method: str | None = None


class NormalizedAnalysis(StrictModel):
    article_id: str
    news_id: str
    context_id: str
    analysis_status: Literal["done", "review", "error"]
    is_risk: Literal["Y", "N"] | None
    urgent: Literal["Y", "N"] | None
    affected_supplier_ids: list[str]
    assessments: list[Assessment]
    model_id: str | None
    question_version: str
    policy_version: str
    error: str | None
    event_type: str | None
    evidence: list[Evidence]
    review_reasons: list[str]
    context_notes: list[str] = Field(default_factory=list)
    source_reading: SourceReading | None = None

    @model_validator(mode="after")
    def consistency(self):
        if self.analysis_status == "error":
            if not self.error or self.is_risk is not None or self.urgent is not None:
                raise ValueError("Un error no tiene decisiones binarias")
        elif self.is_risk is None or self.urgent is None or self.error is not None:
            raise ValueError("Resultado incompleto")
        if len(set(self.affected_supplier_ids)) != len(self.affected_supplier_ids):
            raise ValueError("IDs repetidos")
        if len({a.supplier_id for a in self.assessments}) != len(self.assessments):
            raise ValueError("Evaluaciones repetidas")
        return self
