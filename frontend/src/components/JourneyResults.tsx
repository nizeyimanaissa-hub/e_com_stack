import type { Journey, JourneyLeg, Station } from "../lib/types";

interface Props {
  journeys: Journey[];
  origin: Station;
  destination: Station;
  onSelectLeg: (leg: JourneyLeg) => void;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function JourneyResults({ journeys, origin, destination, onSelectLeg }: Props) {
  if (journeys.length === 0) {
    return <p>No journeys found.</p>;
  }

  return (
    <div className="journey-results">
      <h2>
        {origin.name} → {destination.name}
      </h2>
      {journeys.map((journey, i) => {
        const transitLegs = journey.legs.filter((l) => l.mode !== "WALK");
        const bookable = journey.transfers === 0 && transitLegs.length === 1;

        return (
          <div className="journey-card" key={i}>
            <div className="journey-summary">
              <span>
                {formatTime(journey.departure)} → {formatTime(journey.arrival)}
              </span>
              <span>{journey.duration_minutes} min</span>
              <span>{journey.transfers === 0 ? "direct" : `${journey.transfers} transfer(s)`}</span>
            </div>
            <div className="journey-legs">
              {transitLegs.map((leg, j) => (
                <div key={j} className="leg">
                  <strong>{leg.line_name ?? leg.mode}</strong>
                  {leg.operator ? ` (${leg.operator})` : ""}
                  <div>
                    {leg.origin_name} {formatTime(leg.departure)} → {leg.destination_name} {formatTime(leg.arrival)}
                  </div>
                </div>
              ))}
            </div>
            {bookable ? (
              <button onClick={() => onSelectLeg(transitLegs[0])}>Book this journey</button>
            ) : (
              <p className="hint">Booking isn't supported yet for journeys with transfers.</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
