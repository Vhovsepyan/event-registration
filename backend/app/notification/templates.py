from dataclasses import dataclass

from app.event.models import Event
from app.ticket.models import Ticket


@dataclass(frozen=True)
class EmailContent:
    subject: str
    body: str


def registration_confirmed_email(event: Event, ticket: Ticket) -> EmailContent:
    return EmailContent(
        subject=f"Registration confirmed: {event.title}",
        body=(
            f"Your registration for {event.title} is confirmed.\n\n"
            f"Event time: {event.starts_at.isoformat()}\n"
            f"Ticket code: {ticket.code}\n\n"
            "Keep this code available for check-in."
        ),
    )


def waitlist_promoted_email(event: Event, ticket: Ticket) -> EmailContent:
    return EmailContent(
        subject=f"You have a seat: {event.title}",
        body=(
            f"A seat is now available for {event.title}, and your registration is confirmed.\n\n"
            f"Event time: {event.starts_at.isoformat()}\n"
            f"Ticket code: {ticket.code}\n\n"
            "Keep this code available for check-in."
        ),
    )


def event_reminder_email(event: Event, ticket: Ticket) -> EmailContent:
    return EmailContent(
        subject=f"Reminder: {event.title} is coming up",
        body=(
            f"This is a reminder that {event.title} starts soon.\n\n"
            f"Event time: {event.starts_at.isoformat()}\n"
            f"Ticket code: {ticket.code}\n\n"
            "Bring this code for check-in."
        ),
    )
