from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.booking import Booking
from app.models.user import User
from app.schemas.booking import BookingOut

router = APIRouter(prefix="/api/v1/me", tags=["me"])


@router.get("/bookings", response_model=list[BookingOut])
async def list_my_bookings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Booking]:
    result = await db.execute(
        select(Booking)
        .where(Booking.user_id == current_user.id)
        .options(selectinload(Booking.items))
        .order_by(Booking.created_at.desc())
    )
    return list(result.scalars().all())
