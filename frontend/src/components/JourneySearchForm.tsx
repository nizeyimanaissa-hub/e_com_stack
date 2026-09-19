import { useState } from "react";
import { StationAutocomplete } from "./StationAutocomplete";
import type { Station } from "../lib/types";

interface Props {
  onSearch: (origin: Station, destination: Station, when: string) => void;
}

function defaultDateTimeLocal(): string {
  const d = new Date(Date.now() + 60 * 60 * 1000); // 1 hour from now
  d.setSeconds(0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function JourneySearchForm({ onSearch }: Props) {
  const [origin, setOrigin] = useState<Station | null>(null);
  const [destination, setDestination] = useState<Station | null>(null);
  const [when, setWhen] = useState(defaultDateTimeLocal());
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!origin || !destination) {
      setError("Pick both an origin and a destination station.");
      return;
    }
    if (origin.eva_id === destination.eva_id) {
      setError("Origin and destination must be different stations.");
      return;
    }
    setError(null);
    onSearch(origin, destination, new Date(when).toISOString());
  }

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <h2>Search journeys</h2>
      <StationAutocomplete label="From" onSelect={setOrigin} />
      <StationAutocomplete label="To" onSelect={setDestination} />
      <label>
        Departure
        <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />
      </label>
      {error && <p className="error">{error}</p>}
      <button type="submit">Search</button>
    </form>
  );
}
