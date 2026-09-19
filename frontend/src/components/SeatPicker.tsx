import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { Booking, Seat, Train } from "../lib/types";

interface Props {
  train: Train;
  onBooked: (booking: Booking) => void;
}

export function SeatPicker({ train, onBooked }: Props) {
  const [seats, setSeats] = useState<Seat[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);

  useEffect(() => {
    setLoading(true);
    api
      .getSeatMap(train.id)
      .then(setSeats)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load seat map"))
      .finally(() => setLoading(false));
  }, [train.id]);

  async function handleBook() {
    if (!selected) return;
    setBooking(true);
    setError(null);
    try {
      const result = await api.createBooking([selected]);
      onBooked(result);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Booking failed");
    } finally {
      setBooking(false);
    }
  }

  if (loading) return <p>Loading seat map…</p>;

  const byCoach = new Map<number, Seat[]>();
  for (const seat of seats) {
    const list = byCoach.get(seat.coach_number) ?? [];
    list.push(seat);
    byCoach.set(seat.coach_number, list);
  }

  return (
    <div className="seat-picker">
      <h2>
        {train.category} {train.number} · {new Date(train.departure).toLocaleString()}
      </h2>
      {[...byCoach.entries()].map(([coachNumber, coachSeats]) => (
        <div key={coachNumber} className="coach">
          <h3>
            Coach {coachNumber} · {coachSeats[0].seat_class} class · €{coachSeats[0].price.toFixed(2)}
          </h3>
          <div className="seat-grid">
            {coachSeats.map((seat) => (
              <button
                key={seat.id}
                disabled={seat.status !== "free"}
                className={`seat seat-${seat.status}${selected === seat.id ? " seat-selected" : ""}`}
                onClick={() => setSelected(seat.id)}
                title={`${seat.seat_number} (${seat.status})`}
              >
                {seat.seat_number}
              </button>
            ))}
          </div>
        </div>
      ))}
      {error && <p className="error">{error}</p>}
      <button disabled={!selected || booking} onClick={handleBook}>
        {booking ? "Booking…" : "Book selected seat"}
      </button>
    </div>
  );
}
