import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.registration.schemas import CancellationRead, RegistrationCreate, RegistrationRead
from app.registration.service import RegistrationService

router = APIRouter(prefix="/api/events/{event_id}/registrations", tags=["registrations"])
service = RegistrationService()


@router.post("", response_model=RegistrationRead, status_code=status.HTTP_201_CREATED)
def register_participant(
    event_id: uuid.UUID,
    data: RegistrationCreate,
    session: Annotated[Session, Depends(get_db_session)],
) -> RegistrationRead:
    return RegistrationRead.model_validate(service.register(session, event_id, data))


@router.post("/{registration_id}/cancel", response_model=CancellationRead)
def cancel_registration(
    event_id: uuid.UUID,
    registration_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> CancellationRead:
    return service.cancel(session, event_id, registration_id)
