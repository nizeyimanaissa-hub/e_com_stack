import type { Booking, Journey, Seat, Station, Train, User } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

let accessToken: string | null = localStorage.getItem("access_token");

export function setAccessToken(token: string | null) {
  accessToken = token;
  if (token) {
    localStorage.setItem("access_token", token);
  } else {
    localStorage.removeItem("access_token");
  }
}

export function getAccessToken() {
  return accessToken;
}

// Native WebSocket can't set an Authorization header, so the access token
// travels as a query param instead (see backend/app/routers/bookings.py's
// booking_live_delays for the matching server-side tradeoff note).
export function liveDelayWsUrl(bookingId: string): string | null {
  if (!accessToken) return null;
  const wsBase = API_BASE.replace(/^http/, "ws");
  return `${wsBase}/api/v1/bookings/${bookingId}/live?token=${encodeURIComponent(accessToken)}`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (response.status === 204) {
    return undefined as T;
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const err = body?.error;
    throw new ApiError(response.status, err?.code ?? "unknown_error", err?.message ?? response.statusText);
  }

  return body as T;
}

export const api = {
  register: (email: string, password: string) =>
    request<User>("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),

  login: (email: string, password: string) =>
    request<{ access_token: string; refresh_token: string; token_type: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>("/api/v1/auth/me"),

  searchStations: (query: string) => request<Station[]>(`/api/v1/stations?query=${encodeURIComponent(query)}`),

  searchJourneys: (from: number, to: number, when: string) => {
    const params = new URLSearchParams({ from: String(from), to: String(to), when });
    return request<Journey[]>(`/api/v1/journeys?${params.toString()}`);
  },

  registerTrainFromLeg: (body: {
    origin_eva: number;
    destination_eva: number;
    line_name: string;
    operator: string | null;
    departure: string;
    arrival: string;
  }) => request<Train>("/api/v1/trains/from-journey-leg", { method: "POST", body: JSON.stringify(body) }),

  getSeatMap: (trainId: string) => request<Seat[]>(`/api/v1/trains/${trainId}/seats`),

  createBooking: (seatIds: string[]) =>
    request<Booking>("/api/v1/bookings", { method: "POST", body: JSON.stringify({ seat_ids: seatIds }) }),

  confirmBooking: (bookingId: string) =>
    request<Booking>(`/api/v1/bookings/${bookingId}/confirm`, { method: "POST" }),

  cancelBooking: (bookingId: string) => request<void>(`/api/v1/bookings/${bookingId}`, { method: "DELETE" }),
};
