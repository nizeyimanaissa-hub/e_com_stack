import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from app.core.db import get_db
from app.core.errors import AppError
from app.models.train import Coach, Seat, Train
from app.schemas.train import RegisterTrainFromLegRequest, SeatOut, TrainCreate, TrainOut
from app.services.seat_map import build_coaches

router = APIRouter(prefix="/api/v1/trains", tags=["trains"])

LINE_NAME_PATTERN = re.compile(r"^([A-ZÄÖÜ]+)\s*(.+)$")


class TrainNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__("Train not found", code="train_not_found", status_code=404)


@router.post("", response_model=TrainOut, status_code=201)
async def create_or_get_train(body: TrainCreate, db: AsyncSession = Depends(get_db)) -> Train:
    """Idempotently registers a concrete train run and generates its (invented)
    seat map on first use, from hand-typed details. For a train that came from
    a real journey search result, use POST /from-journey-leg instead.
    """
    return await _get_or_create_train(
        db,
        category=body.category,
        number=body.number,
        operator=body.operator,
        origin_eva=body.origin_eva,
        destination_eva=body.destination_eva,
        departure=body.departure,
        arrival=body.arrival,
    )


@router.post("/from-journey-leg", response_model=TrainOut, status_code=201)
async def register_train_from_leg(body: RegisterTrainFromLegRequest, db: AsyncSession = Depends(get_db)) -> Train:
    """Idempotently registers the train for one selected leg of a real
    GET /api/v1/journeys result (a direct, transfers=0 journey -- the leg's
    origin/destination are then exactly the queried origin_eva/destination_eva).
    """
    category, number = _parse_line_name(body.line_name)
    return await _get_or_create_train(
        db,
        category=category,
        number=number,
        operator=body.operator or "unknown",
        origin_eva=body.origin_eva,
        destination_eva=body.destination_eva,
        departure=body.departure,
        arrival=body.arrival,
    )


async def _get_or_create_train(
    db: AsyncSession,
    *,
    category: str,
    number: str,
    operator: str,
    origin_eva: int,
    destination_eva: int,
    departure: datetime,
    arrival: datetime,
) -> Train:
    result = await db.execute(
        select(Train).where(Train.category == category, Train.number == number, Train.departure == departure)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    train = Train(
        category=category,
        number=number,
        operator=operator,
        origin_eva=origin_eva,
        destination_eva=destination_eva,
        departure=departure,
        arrival=arrival,
        coaches=build_coaches(),
    )
    db.add(train)
    await db.commit()
    await db.refresh(train)
    return train


def _parse_line_name(line_name: str) -> tuple[str, str]:
    """"ICE 76" -> ("ICE", "76"); "RE4 (82016)" -> ("RE", "4 (82016)")."""
    match = LINE_NAME_PATTERN.match(line_name.strip())
    if not match:
        return "UNKNOWN", line_name.strip()
    return match.group(1), match.group(2).strip()


@router.get("/{train_id}/seats", response_model=list[SeatOut])
async def get_seat_map(train_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[SeatOut]:
    result = await db.execute(
        select(Seat)
        .join(Coach)
        .where(Coach.train_id == train_id)
        .options(contains_eager(Seat.coach))
        .order_by(Coach.coach_number, Seat.seat_number)
    )
    seats = result.scalars().all()
    if not seats:
        # either the train doesn't exist, or it exists with no seats generated --
        # both cases are "nothing to show" for this endpoint
        raise TrainNotFoundError()

    now = datetime.now(timezone.utc)
    return [
        SeatOut(
            id=seat.id,
            coach_number=seat.coach.coach_number,
            seat_class=seat.coach.seat_class,
            seat_number=seat.seat_number,
            price=float(seat.coach.price),
            status="free" if _hold_expired(seat, now) else seat.status,
        )
        for seat in seats
    ]


def _hold_expired(seat: Seat, now: datetime) -> bool:
    return seat.status == "held" and seat.held_until is not None and seat.held_until < now
