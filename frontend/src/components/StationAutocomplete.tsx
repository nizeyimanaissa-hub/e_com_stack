import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { Station } from "../lib/types";

interface Props {
  label: string;
  onSelect: (station: Station) => void;
}

export function StationAutocomplete({ label, onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Station[]>([]);
  const [selected, setSelected] = useState<Station | null>(null);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (selected || query.trim().length < 2) {
      setResults([]);
      return;
    }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const stations = await api.searchStations(query.trim());
        setResults(stations);
        setOpen(true);
      } catch {
        setResults([]);
      }
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [query, selected]);

  return (
    <div className="autocomplete">
      <label>
        {label}
        <input
          value={selected ? selected.name : query}
          onChange={(e) => {
            setSelected(null);
            setQuery(e.target.value);
          }}
          onFocus={() => setOpen(true)}
          placeholder="Station name, e.g. Frankfurt"
        />
      </label>
      {open && results.length > 0 && (
        <ul className="autocomplete-list">
          {results.map((s) => (
            <li
              key={s.eva_id}
              onClick={() => {
                setSelected(s);
                setQuery(s.name);
                setOpen(false);
                onSelect(s);
              }}
            >
              {s.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
