from dataclasses import dataclass

from app.event.models import Event
from app.ticket.models import Ticket


@dataclass(frozen=True)
class EmailContent:
    subject: str
    body: str


def _manage_footer(manage_url: str) -> str:
    return f"\n\nView or cancel your registration at any time:\n{manage_url}"


def registration_confirmed_email(event: Event, ticket: Ticket, manage_url: str) -> EmailContent:
    return EmailContent(
        subject=f"Registration confirmed: {event.title}",
        body=(
            f"Your registration for {event.title} is confirmed.\n\n"
            f"Event time: {event.starts_at.isoformat()}\n"
            f"Ticket code: {ticket.code}\n\n"
            "Keep this code available for check-in." + _manage_footer(manage_url)
        ),
    )


def waitlist_joined_email(event: Event, position: int, manage_url: str) -> EmailContent:
    return EmailContent(
        subject=f"You're on the waiting list: {event.title}",
        body=(
            f"{event.title} is currently full, so you are on the waiting list.\n\n"
            f"Event time: {event.starts_at.isoformat()}\n"
            f"Your place in line: {position}\n\n"
            "If a seat frees up you are moved up automatically and receive your ticket by email."
            + _manage_footer(manage_url)
        ),
    )


def waitlist_promoted_email(event: Event, ticket: Ticket, manage_url: str) -> EmailContent:
    return EmailContent(
        subject=f"You have a seat: {event.title}",
        body=(
            f"A seat is now available for {event.title}, and your registration is confirmed.\n\n"
            f"Event time: {event.starts_at.isoformat()}\n"
            f"Ticket code: {ticket.code}\n\n"
            "Keep this code available for check-in." + _manage_footer(manage_url)
        ),
    )


def event_reminder_email(event: Event, ticket: Ticket, manage_url: str) -> EmailContent:
    return EmailContent(
        subject=f"Reminder: {event.title} is coming up",
        body=(
            f"This is a reminder that {event.title} starts soon.\n\n"
            f"Event time: {event.starts_at.isoformat()}\n"
            f"Ticket code: {ticket.code}\n\n"
            "Bring this code for check-in." + _manage_footer(manage_url)
        ),
    )


def event_rescheduled_email(
    event: Event, old_starts_at: str, new_starts_at: str, manage_url: str
) -> EmailContent:
    return EmailContent(
        subject=f"New event time: {event.title}",
        body=(
            f"The schedule for {event.title} has changed.\n\n"
            f"Previous time: {old_starts_at}\n"
            f"New time: {new_starts_at}\n\n"
            "Please update your plans." + _manage_footer(manage_url)
        ),
    )
