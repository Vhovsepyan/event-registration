import secrets
import uuid

from sqlalchemy.orm import Session

from app.common.errors import ResourceNotFoundError
from app.event.schemas import EventRead
from app.ticket.models import Ticket
from app.ticket.repository import TicketRepository
from app.ticket.schemas import CheckInRead, CheckInResult, TicketDetails, TicketRead

TICKET_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_ticket_code() -> str:
    characters = "".join(secrets.choice(TICKET_ALPHABET) for _ in range(12))
    return "-".join(characters[index : index + 4] for index in range(0, 12, 4))


class TicketService:
    def __init__(self, repository: TicketRepository | None = None) -> None:
        self.repository = repository or TicketRepository()

    def issue(self, session: Session, registration_id: uuid.UUID) -> Ticket:
        ticket = Ticket(registration_id=registration_id, code=generate_ticket_code())
        self.repository.add(session, ticket)
        return ticket

    def get_details(self, session: Session, code: str) -> TicketDetails:
        normalized_code = code.strip().upper()
        ticket = self.repository.get_by_code(session, normalized_code)
        if ticket is None:
            raise ResourceNotFoundError("Ticket", normalized_code)
        return TicketDetails(
            **TicketRead.model_validate(ticket).model_dump(),
            event=EventRead.model_validate(ticket.registration.event),
            registration_status=ticket.registration.status,
        )

    def check_in(self, session: Session, code: str) -> CheckInRead:
        normalized_code = code.strip().upper()
        with session.begin():
            ticket = self.repository.check_in(session, normalized_code)
            if ticket is not None:
                return CheckInRead(result=CheckInResult.SUCCESS, checked_in_at=ticket.checked_in_at)

            existing = self.repository.get_by_code(session, normalized_code)
            if (
                existing is not None
                and existing.invalidated_at is None
                and existing.checked_in_at is not None
            ):
                return CheckInRead(
                    result=CheckInResult.ALREADY_CHECKED_IN,
                    checked_in_at=existing.checked_in_at,
                )
            return CheckInRead(result=CheckInResult.INVALID_TICKET)
