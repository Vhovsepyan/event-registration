import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

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
