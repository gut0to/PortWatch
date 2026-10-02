"use strict";

export async function getJson(url, options = {}) {
  const response = await fetch(url, {
    cache: "no-store",
    headers: { Accept: "application/json", ...options.headers },
    ...options,
  });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("The local dashboard returned an unreadable response.");
  }
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
  return data;
}

export function parseRange(elements) {
  const start = Number(elements.rangeStart.value);
  const end = Number(elements.rangeEnd.value);
  const valid = Number.isInteger(start) && Number.isInteger(end) && start >= 1 && end <= 65535 && start <= end;
  elements.rangeStart.setAttribute("aria-invalid", String(!valid));
  elements.rangeEnd.setAttribute("aria-invalid", String(!valid));
  if (!valid) throw new Error("Enter a port range from 1 to 65535, with the start at or below the end.");
  return { start, end };
}

export function fetchPorts(range) {
  return getJson(`/api/ports?start=${range.start}&end=${range.end}`);
}

export function terminatePort(port, token) {
  return getJson(`/api/ports/${port.port}/terminate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-PortWatch-Token": token,
    },
    body: JSON.stringify({ pid: port.pid }),
  });
}
