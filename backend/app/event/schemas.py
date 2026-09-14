import uuid
from datetime import UTC, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class EventCreate(BaseModel):
    title: str = Field(max_length=200)
    description: str = Field(default="", max_length=10_000)
    starts_at: AwareDatetime
    capacity: int = Field(gt=0)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title must not be blank")
        return title

    @field_validator("starts_at")
    @classmethod
    def starts_at_must_be_in_the_future(cls, value: datetime) -> datetime:
        if value <= datetime.now(UTC):
            raise ValueError("starts_at must be in the future")
        return value


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    starts_at: datetime
    capacity: int
    created_at: datetime
    updated_at: datetime


class EventReschedule(BaseModel):
    starts_at: AwareDatetime

    @field_validator("starts_at")
    @classmethod
    def starts_at_must_be_in_the_future(cls, value: datetime) -> datetime:
        if value <= datetime.now(UTC):
            raise ValueError("starts_at must be in the future")
        return value
