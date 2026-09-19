import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.models.booking import Booking, BookingItem, Payment
from app.models.train import Seat
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingOut

router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])


class NoSeatsRequestedError(AppError):
    def __init__(self) -> None:
        super().__init__("At least one seat is required", code="no_seats", status_code=400)


class UnknownSeatsError(AppError):
    def __init__(self, seat_ids: set[uuid.UUID]) -> None:
        ids = ", ".join(str(s) for s in seat_ids)
        super().__init__(f"Unknown seat id(s): {ids}", code="unknown_seats", status_code=400)


class SeatsUnavailableError(AppError):
    def __init__(self, seat_ids: list[uuid.UUID]) -> None:
        ids = ", ".join(str(s) for s in seat_ids)
        super().__init__(f"Seat(s) no longer available: {ids}", code="seats_unavailable", status_code=409)


class BookingNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__("Booking not found", code="booking_not_found", status_code=404)


class InvalidBookingStateError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_booking_state", status_code=409)


@router.post("", response_model=BookingOut, status_code=201)
async def create_booking(
    body: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Booking:
    if not body.seat_ids:
        raise NoSeatsRequestedError()

    now = datetime.now(timezone.utc)

    # SELECT ... FOR UPDATE locks these exact seat rows for the rest of this
    # transaction. If two requests race for the same seat, the second one's
    # SELECT blocks here until the first transaction commits or rolls back --
    # it then sees the first transaction's write (status='held') and correctly
    # rejects, instead of both requests reading "free" and both succeeding.
    result = await db.execute(
        select(Seat)
        .where(Seat.id.in_(body.seat_ids))
        .options(selectinload(Seat.coach))
        .with_for_update()
    )
    seats = {seat.id: seat for seat in result.scalars().all()}

    missing = set(body.seat_ids) - seats.keys()
    if missing:
        raise UnknownSeatsError(missing)

    unavailable = [seat.id for seat in seats.values() if not _is_available(seat, now)]
    if unavailable:
        raise SeatsUnavailableError(unavailable)

    hold_until = now + timedelta(minutes=settings.seat_hold_minutes)

    booking = Booking(user_id=current_user.id, status="pending")
    for seat_id in body.seat_ids:
        seat = seats[seat_id]
        seat.status = "held"
        seat.held_until = hold_until
        booking.items.append(BookingItem(seat_id=seat.id, train_id=seat.coach.train_id, price=seat.coach.price))

    db.add(booking)
    await db.commit()
    await db.refresh(booking, attribute_names=["items"])
    return booking


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Booking:
    booking = await _get_owned_booking(booking_id, current_user, db)
    return booking


@router.post("/{booking_id}/confirm", response_model=BookingOut)
async def confirm_booking(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Booking:
    booking = await _get_owned_booking(booking_id, current_user, db)
    if booking.status != "pending":
        raise InvalidBookingStateError(f"Booking is '{booking.status}', can only confirm a pending booking")

    now = datetime.now(timezone.utc)
    seat_ids = [item.seat_id for item in booking.items]
    result = await db.execute(select(Seat).where(Seat.id.in_(seat_ids)).with_for_update())
    seats = {seat.id: seat for seat in result.scalars().all()}

    expired = [
        seat_id
        for seat_id in seat_ids
        if seats[seat_id].status != "held" or _hold_expired(seats[seat_id], now)
    ]
    if expired:
        raise InvalidBookingStateError("Your seat hold has expired; please book again")

    for seat_id in seat_ids:
        seats[seat_id].status = "booked"
        seats[seat_id].held_until = None

    booking.status = "confirmed"
    total = sum(item.price for item in booking.items)
    db.add(
        Payment(
            booking_id=booking.id,
            status="succeeded",  # always succeeds -- this is a mock payment, per the spec's non-goals
            amount=total,
            mock_provider_ref=f"mock_{uuid.uuid4().hex[:12]}",
        )
    )

    await db.commit()
    await db.refresh(booking, attribute_names=["items"])
    return booking


@router.delete("/{booking_id}", status_code=204)
async def cancel_booking(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    booking = await _get_owned_booking(booking_id, current_user, db)
    if booking.status != "pending":
        raise InvalidBookingStateError(f"Cannot cancel a booking with status '{booking.status}'")

    seat_ids = [item.seat_id for item in booking.items]
    result = await db.execute(select(Seat).where(Seat.id.in_(seat_ids)).with_for_update())
    for seat in result.scalars().all():
        seat.status = "free"
        seat.held_until = None

    booking.status = "cancelled"
    await db.commit()


async def _get_owned_booking(booking_id: uuid.UUID, current_user: User, db: AsyncSession) -> Booking:
    booking = await db.get(Booking, booking_id, options=[selectinload(Booking.items)])
    # 404 (not 403) when it's someone else's booking -- don't reveal that a
    # booking id belongs to another user.
    if booking is None or booking.user_id != current_user.id:
        raise BookingNotFoundError()
    return booking


def _hold_expired(seat: Seat, now: datetime) -> bool:
    return seat.status == "held" and seat.held_until is not None and seat.held_until < now


def _is_available(seat: Seat, now: datetime) -> bool:
    if seat.status == "free":
        return True
    return _hold_expired(seat, now)
