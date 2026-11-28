// Rendering helpers for instants coming from the API.
//
// The API sends a full instant with its UTC offset (for example
// "2026-11-28T18:36:12+00:00"). Before, it sent a pre-formatted "HH:MM" built
// from UTC, so a reader in Tunis saw an hour less than the clock on their wall
// and the interface had no way to correct it. Formatting belongs here.

/** Hour and minute in the reader's own time zone. */
export function localTime(at?: string | null, fallback = ""): string {
  if (!at) return fallback;
  const moment = new Date(at);
  if (Number.isNaN(moment.getTime())) return fallback;
  return moment.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

/** Date and time in the reader's own time zone, for tooltips. */
export function localDateTime(at?: string | null, fallback = ""): string {
  if (!at) return fallback;
  const moment = new Date(at);
  if (Number.isNaN(moment.getTime())) return fallback;
  return moment.toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
