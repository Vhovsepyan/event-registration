from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.ticket.schemas import TicketDetails
from app.ticket.service import TicketService

router = APIRouter(prefix="/api/tickets", tags=["tickets"])
service = TicketService()


@router.get("/{code}", response_model=TicketDetails)
def get_ticket(code: str, session: Annotated[Session, Depends(get_db_session)]) -> TicketDetails:
    return service.get_details(session, code)
