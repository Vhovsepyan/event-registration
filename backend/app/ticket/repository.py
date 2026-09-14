from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.registration.models import Registration
from app.ticket.models import Ticket


class TicketRepository:
    def add(self, session: Session, ticket: Ticket) -> None:
        session.add(ticket)

    def get_by_code(self, session: Session, code: str) -> Ticket | None:
        statement = (
            select(Ticket)
            .where(Ticket.code == code)
            .options(joinedload(Ticket.registration).joinedload(Registration.event))
        )
        return session.scalar(statement)
