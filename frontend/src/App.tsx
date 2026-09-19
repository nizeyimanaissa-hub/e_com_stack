import { useState } from "react";
import { AuthForm } from "./components/AuthForm";
import { JourneySearchForm } from "./components/JourneySearchForm";
import { JourneyResults } from "./components/JourneyResults";
import { SeatPicker } from "./components/SeatPicker";
import { BookingConfirmation } from "./components/BookingConfirmation";
import { api, ApiError, getAccessToken, setAccessToken } from "./lib/api";
import type { Booking, Journey, JourneyLeg, Station, Train } from "./lib/types";

type Step =
  | { name: "auth" }
  | { name: "search" }
  | { name: "results"; origin: Station; destination: Station; journeys: Journey[] }
  | { name: "seats"; train: Train }
  | { name: "confirmation"; booking: Booking };

export default function App() {
  const [step, setStep] = useState<Step>(getAccessToken() ? { name: "search" } : { name: "auth" });
  const [error, setError] = useState<string | null>(null);
  const [searchOrigin, setSearchOrigin] = useState<Station | null>(null);
  const [searchDestination, setSearchDestination] = useState<Station | null>(null);

  function logout() {
    setAccessToken(null);
    setStep({ name: "auth" });
  }

  async function handleSearch(origin: Station, destination: Station, when: string) {
    setError(null);
    setSearchOrigin(origin);
    setSearchDestination(destination);
    try {
      const journeys = await api.searchJourneys(origin.eva_id, destination.eva_id, when);
      setStep({ name: "results", origin, destination, journeys });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Journey search failed");
    }
  }

  async function handleSelectLeg(leg: JourneyLeg) {
    if (!searchOrigin || !searchDestination) return;
    setError(null);
    try {
      const train = await api.registerTrainFromLeg({
        origin_eva: searchOrigin.eva_id,
        destination_eva: searchDestination.eva_id,
        line_name: leg.line_name ?? leg.mode,
        operator: leg.operator,
        departure: leg.departure,
        arrival: leg.arrival,
      });
      setStep({ name: "seats", train });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not register this train for booking");
    }
  }

  return (
    <div className="app">
      <header>
        <h1>RailBoard</h1>
        {getAccessToken() && (
          <button className="link" onClick={logout}>
            Log out
          </button>
        )}
      </header>
      {error && <p className="error global-error">{error}</p>}

      {step.name === "auth" && <AuthForm onAuthenticated={() => setStep({ name: "search" })} />}

      {step.name === "search" && <JourneySearchForm onSearch={handleSearch} />}

      {step.name === "results" && (
        <>
          <JourneyResults
            journeys={step.journeys}
            origin={step.origin}
            destination={step.destination}
            onSelectLeg={handleSelectLeg}
          />
          <button className="link" onClick={() => setStep({ name: "search" })}>
            ← New search
          </button>
        </>
      )}

      {step.name === "seats" && (
        <SeatPicker train={step.train} onBooked={(booking) => setStep({ name: "confirmation", booking })} />
      )}

      {step.name === "confirmation" && (
        <BookingConfirmation booking={step.booking} onDone={() => setStep({ name: "search" })} />
      )}
    </div>
  );
}
