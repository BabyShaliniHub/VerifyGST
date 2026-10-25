from typing import Literal

from pydantic import BaseModel


class ComponentStatus(BaseModel):
    name: str
    state: Literal["connected", "not_configured", "unavailable", "authentication_failed", "error"]
    detail: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    components: list[ComponentStatus]
