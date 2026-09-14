import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.registration.models import RegistrationStatus
from app.ticket.schemas import TicketRead


class RegistrationCreate(BaseModel):
    email: EmailStr


class RegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    email: str
    status: RegistrationStatus
    waitlist_order: int | None
    created_at: datetime
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    ticket: TicketRead | None
