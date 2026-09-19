import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookingCreate(BaseModel):
    seat_ids: list[uuid.UUID]


class BookingItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seat_id: uuid.UUID
    train_id: uuid.UUID
    price: float


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    created_at: datetime
    items: list[BookingItemOut]
