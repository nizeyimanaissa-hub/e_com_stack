import { useEffect, useState } from "react";
import { liveDelayWsUrl } from "../lib/api";
import type { DelayUpdate } from "../lib/types";

interface Props {
  bookingId: string;
}

export function LiveDelayPanel({ bookingId }: Props) {
  const [update, setUpdate] = useState<DelayUpdate | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const url = liveDelayWsUrl(bookingId);
    if (!url) return;

    const ws = new WebSocket(url);
    ws.onopen = () => setConnected(true);
    ws.onmessage = (event) => setUpdate(JSON.parse(event.data) as DelayUpdate);
    ws.onclose = () => setConnected(false);

    return () => ws.close();
  }, [bookingId]);

  if (!update) {
    return <p className="live-delay hint">Connecting to live delay feed…</p>;
  }

  const label =
    update.status === "arrived"
      ? "Arrived"
      : update.status === "delayed"
        ? `Delayed +${update.delay_minutes} min`
        : "On time";

  return (
    <p className={`live-delay live-delay-${update.status}`}>
      <span className="live-delay-dot" />
      {label}
      {!connected && update.status !== "arrived" && " (feed disconnected)"}
      <span className="hint"> — simulated live feed, updates every couple of seconds</span>
    </p>
  );
}
