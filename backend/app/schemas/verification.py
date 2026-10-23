"""Request and response shapes for the verification API."""

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.invoice_authentication.comparison import COMPARED_FIELDS

StatusName = Literal["passed", "failed", "unknown", "not_checked", "manual_review"]


class VisibleFieldIn(BaseModel):
    """One value read from the document and the reader's confidence from 0 to 1."""

    model_config = ConfigDict(extra="forbid")

    value: str | None = Field(default=None, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)


class SignedEnvelopeIn(BaseModel):
    """Signed data found on the document. It is untrusted until the signature verifies."""

    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any]
    signature: str = Field(max_length=200)
    key_id: str | None = Field(default=None, max_length=64)

    @field_validator("payload")
    @classmethod
    def _payload_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 30 or len(json.dumps(value, default=str)) > 8000:
            raise ValueError("payload is too large")
        return value


class VerificationRequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visible: dict[str, VisibleFieldIn] = Field(default_factory=dict, max_length=20)
    envelope: SignedEnvelopeIn | None = None
    file_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("visible")
    @classmethod
    def _known_fields(cls, value: dict[str, VisibleFieldIn]) -> dict[str, VisibleFieldIn]:
        unknown = set(value) - set(COMPARED_FIELDS)
        if unknown:
            raise ValueError("unknown field name in visible")
        return value


class CheckOut(BaseModel):
    id: str
    label: str
    status: StatusName
    detail: str


class FieldComparisonOut(BaseModel):
    field: str
    label: str
    visible: str | None
    signed: str | None
    status: StatusName


class VerificationReportOut(BaseModel):
    """Every check keeps its own result. There is deliberately no overall verdict."""

    checks: list[CheckOut]
    field_comparisons: list[FieldComparisonOut]
    next_actions: list[str]


class SampleFieldOut(BaseModel):
    field: str
    label: str
    value: str | None
    confidence: float
    unclear: bool


class SampleOut(BaseModel):
    id: str
    label: str
    visible: list[SampleFieldOut]
