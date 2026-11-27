from fastapi import APIRouter, Depends, Query
from neo4j import Driver
from sqlalchemy import Connection

from app.analysis.findings import Finding, check_results
from app.analysis.service import FindingSet, analyse_cycles
from app.api.dependencies import get_connection, get_driver
from app.api.errors import ApiError, translate_backend_errors
from app.schemas.findings import (
    CheckOut,
    CompanyRef,
    FindingOut,
    FindingsResponse,
    NotEvaluatedOut,
    SignalOut,
)

router = APIRouter(prefix="/api/v1", tags=["findings"])

SEARCH_TIMEOUT_SECONDS = 5.0


def _finding_out(finding: Finding) -> FindingOut:
    return FindingOut(
        companies=[CompanyRef(id=i, name=n) for i, n in zip(finding.company_ids, finding.company_names)],
        transaction_ids=list(finding.transaction_ids),
        summary=finding.summary,
        priority=finding.priority,
        priority_explanation=finding.priority_explanation,
        signals=[
            SignalOut(
                code=s.code,
                title=s.title,
                observed=s.observed,
                may_indicate=s.may_indicate,
                does_not_prove=s.does_not_prove,
                transaction_ids=list(s.transaction_ids),
            )
            for s in finding.signals
        ],
        not_evaluated=[NotEvaluatedOut(code=n.code, reason=n.reason) for n in finding.not_evaluated],
        checks=[CheckOut(code=c.code, title=c.title, result=c.result) for c in check_results(finding)],
        disclaimer=finding.disclaimer,
    )


def _response(result: FindingSet) -> FindingsResponse:
    return FindingsResponse(
        findings=[_finding_out(f) for f in result.findings],
        truncated=result.truncated,
        min_length=result.min_length,
        max_length=result.max_length,
    )


@router.get("/findings", response_model=FindingsResponse)
def get_findings(
    min_length: int = Query(3, ge=2, le=8, description="Shortest cycle to look for."),
    max_length: int = Query(6, ge=2, le=8, description="Longest cycle to look for."),
    max_results: int = Query(50, ge=1, le=500, description="Most cycles to return."),
    connection: Connection = Depends(get_connection),
    driver: Driver = Depends(get_driver),
) -> FindingsResponse:
    """Trading loops with the signals found in each. Indicators for review, not proof of fraud."""
    if min_length > max_length:
        raise ApiError(422, "invalid_request", "min_length must not be larger than max_length.")
    with translate_backend_errors():
        result = analyse_cycles(
            connection,
            driver,
            min_length=min_length,
            max_length=max_length,
            max_results=max_results,
            timeout_seconds=SEARCH_TIMEOUT_SECONDS,
        )
    return _response(result)
