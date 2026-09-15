import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query, status

from app.common.config import Settings, get_settings

ORGANIZER_KEY_HEADER = "X-Organizer-Key"


def require_organizer_key(
    settings: Annotated[Settings, Depends(get_settings)],
    header_key: Annotated[str | None, Header(alias=ORGANIZER_KEY_HEADER)] = None,
    query_key: Annotated[str | None, Query(alias="organizer_key")] = None,
) -> None:
    """Gate organizer and staff routes behind a shared secret when one is configured.

    Unset locally, so the development and test experience is unchanged. The query form exists
    only because the browser's EventSource cannot send headers to the statistics stream.
    """
    expected = settings.organizer_key
    if expected is None:
        return
    supplied = header_key if header_key is not None else query_key
    if supplied is None or not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This action requires the organizer key",
            headers={"WWW-Authenticate": ORGANIZER_KEY_HEADER},
        )
