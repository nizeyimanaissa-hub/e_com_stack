export interface Station {
  eva_id: number;
  name: string;
  ds100: string | null;
  lat: number | null;
  lon: number | null;
  federal_state: string | null;
}

export interface JourneyLeg {
  mode: string;
  origin_name: string;
  destination_name: string;
  departure: string;
  arrival: string;
  line_name: string | null;
  operator: string | null;
}

export interface Journey {
  legs: JourneyLeg[];
  departure: string;
  arrival: string;
  duration_minutes: number;
  transfers: number;
  price_amount: number | null;
  price_currency: string | null;
}

export interface Train {
  id: string;
  category: string;
  number: string;
  operator: string;
  origin_eva: number;
  destination_eva: number;
  departure: string;
  arrival: string;
}

export interface Seat {
  id: string;
  coach_number: number;
  seat_class: string;
  seat_number: string;
  price: number;
  status: "free" | "held" | "booked";
}

export interface BookingItem {
  seat_id: string;
  train_id: string;
  price: number;
}

export interface Booking {
  id: string;
  status: "pending" | "confirmed" | "cancelled";
  created_at: string;
  items: BookingItem[];
}

export interface User {
  id: string;
  email: string;
  created_at: string;
}
