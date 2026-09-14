import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.event.schemas import EventRead
from app.registration.models import RegistrationStatus


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    registration_id: uuid.UUID
    code: str
    created_at: datetime
    checked_in_at: datetime | None
    invalidated_at: datetime | None


class TicketDetails(TicketRead):
    event: EventRead
    registration_status: RegistrationStatus


class CheckInResult(StrEnum):
    SUCCESS = "SUCCESS"
    ALREADY_CHECKED_IN = "ALREADY_CHECKED_IN"
    INVALID_TICKET = "INVALID_TICKET"


class CheckInCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)


class CheckInRead(BaseModel):
    result: CheckInResult
    checked_in_at: datetime | None = None
