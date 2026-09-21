import { useState } from "react";
import { api, ApiError } from "../lib/api";
import type { Booking } from "../lib/types";
import { LiveDelayPanel } from "./LiveDelayPanel";

interface Props {
  booking: Booking;
  onDone: () => void;
}

export function BookingConfirmation({ booking: initial, onDone }: Props) {
  const [booking, setBooking] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  async function handleConfirm() {
    setWorking(true);
    setError(null);
    try {
      setBooking(await api.confirmBooking(booking.id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to confirm booking");
    } finally {
      setWorking(false);
    }
  }

  async function handleCancel() {
    setWorking(true);
    setError(null);
    try {
      await api.cancelBooking(booking.id);
      setBooking({ ...booking, status: "cancelled" });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to cancel booking");
    } finally {
      setWorking(false);
    }
  }

  const total = booking.items.reduce((sum, item) => sum + item.price, 0);

  return (
    <div className="booking-confirmation">
      <h2>Booking {booking.id.slice(0, 8)}</h2>
      <p>
        Status: <strong>{booking.status}</strong>
      </p>
      <p>Seats: {booking.items.length}</p>
      <p>Total: €{total.toFixed(2)}</p>
      {booking.status === "confirmed" && <LiveDelayPanel bookingId={booking.id} />}
      {error && <p className="error">{error}</p>}
      {booking.status === "pending" && (
        <div className="actions">
          <button onClick={handleConfirm} disabled={working}>
            Confirm (mock payment)
          </button>
          <button onClick={handleCancel} disabled={working} className="secondary">
            Cancel
          </button>
        </div>
      )}
      {booking.status !== "pending" && <button onClick={onDone}>Search another journey</button>}
    </div>
  );
}
