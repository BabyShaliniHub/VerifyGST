"""Verification endpoints: the real pipeline, plus a synthetic demonstration set."""

import dataclasses
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Request

from app.schemas.verification import (
    CheckOut,
    FieldComparisonOut,
    SampleFieldOut,
    SampleOut,
    VerificationReportOut,
    VerificationRequestIn,
)
from app.services.demo.environment import DemoEnvironment, DemoSample
from app.services.invoice_authentication.comparison import FIELD_LABELS, VisibleField
from app.services.invoice_authentication.pipeline import SignedEnvelope, VerificationRequest
from app.services.invoice_authentication.results import VerificationReport

router = APIRouter(prefix="/api/v1", tags=["verification"])

# Matches the pipeline's default confidence threshold. Used only to mark fields as unclear.
UNCLEAR_BELOW = 0.85


def get_demo(request: Request) -> DemoEnvironment:
    return request.app.state.demo


def _today():
    return datetime.now(timezone.utc).date()


def _label(field: str) -> str:
    text = FIELD_LABELS.get(field, field)
    return text[:1].upper() + text[1:]


def _to_domain(body: VerificationRequestIn) -> VerificationRequest:
    visible = {name: VisibleField(item.value, item.confidence) for name, item in body.visible.items()}
    envelope = None
    if body.envelope is not None:
        envelope = SignedEnvelope(body.envelope.payload, body.envelope.signature, body.envelope.key_id)
    return VerificationRequest(visible, envelope, _today(), body.file_sha256)


def _report_out(report: VerificationReport) -> VerificationReportOut:
    return VerificationReportOut(
        checks=[
            CheckOut(id=c.check_id, label=c.label, status=c.status.value, detail=c.detail)
            for c in report.checks
        ],
        field_comparisons=[
            FieldComparisonOut(
                field=f.field,
                label=_label(f.field),
                visible=f.visible,
                signed=f.signed,
                status=f.status.value,
            )
            for f in report.fields
        ],
        next_actions=list(report.next_actions),
    )


def _sample_out(sample: DemoSample) -> SampleOut:
    return SampleOut(
        id=sample.sample_id,
        label=sample.label,
        visible=[
            SampleFieldOut(
                field=name,
                label=_label(name),
                value=item.value,
                confidence=item.confidence,
                unclear=item.confidence < UNCLEAR_BELOW,
            )
            for name, item in sample.request.visible.items()
        ],
    )


@router.post("/verifications", response_model=VerificationReportOut)
def verify_invoice(
    body: VerificationRequestIn, demo: DemoEnvironment = Depends(get_demo)
) -> VerificationReportOut:
    """Run every check on the submitted fields and signed data. Unknown issuers are Unknown."""
    return _report_out(demo.pipeline.verify(_to_domain(body)))


@router.get("/demo/samples", response_model=list[SampleOut])
def list_samples(demo: DemoEnvironment = Depends(get_demo)) -> list[SampleOut]:
    """The synthetic sample invoices. They describe no real company or account."""
    return [_sample_out(s) for s in demo.samples]


@router.post("/demo/samples/{sample_id}/verify", response_model=VerificationReportOut)
def verify_sample(
    sample_id: str = Path(pattern=r"^[a-z0-9-]{1,40}$"),
    demo: DemoEnvironment = Depends(get_demo),
) -> VerificationReportOut:
    """Run a synthetic sample through the real pipeline."""
    sample = demo.sample(sample_id)
    if sample is None:
        raise HTTPException(status_code=404, detail="Unknown sample invoice.")
    request = dataclasses.replace(sample.request, verification_date=_today())
    return _report_out(demo.pipeline.verify(request))
