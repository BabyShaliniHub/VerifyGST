from typing import Literal

from pydantic import BaseModel


class CompanyRef(BaseModel):
    id: str
    name: str


class SignalOut(BaseModel):
    code: str
    title: str
    observed: str
    may_indicate: str
    does_not_prove: str
    transaction_ids: list[str]


class NotEvaluatedOut(BaseModel):
    code: str
    reason: str


class CheckOut(BaseModel):
    code: str
    title: str
    result: Literal["triggered", "not_triggered", "not_evaluated"]


class FindingOut(BaseModel):
    companies: list[CompanyRef]  # in trade order; the last one sells back to the first
    transaction_ids: list[str]  # transaction i goes from company i to company i + 1
    summary: str
    priority: Literal["low", "medium", "high"]
    priority_explanation: str
    signals: list[SignalOut]
    not_evaluated: list[NotEvaluatedOut]
    checks: list[CheckOut]
    disclaimer: str


class FindingsResponse(BaseModel):
    findings: list[FindingOut]
    truncated: bool  # true means the search stopped at its limit, so the list is incomplete
    min_length: int
    max_length: int
