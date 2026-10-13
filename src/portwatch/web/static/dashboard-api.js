"use strict";

export async function getJson(url, options = {}) {
  const response = await fetch(url, {
    cache: "no-store",
    ...options,
    headers: { Accept: "application/json", ...options.headers },
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
  const decimal = /^\d{1,5}$/;
  const valid = decimal.test(elements.rangeStart.value) && decimal.test(elements.rangeEnd.value) && Number.isInteger(start) && Number.isInteger(end) && start >= 1 && end <= 65535 && start <= end;
  elements.rangeStart.setAttribute("aria-invalid", String(!valid));
  elements.rangeEnd.setAttribute("aria-invalid", String(!valid));
  if (!valid) throw new Error("Enter a port range from 1 to 65535, with the start at or below the end.");
  return { start, end };
}

export async function fetchPorts(range) {
  const data = await getJson(`/api/ports?start=${range.start}&end=${range.end}`);
  const textFields = ["process_name", "project_name", "command", "working_directory", "started_at"];
  if (!data || !Array.isArray(data.ports) || typeof data.scanned_at !== "string" ||
      !data.ports.every((port) => port && Number.isInteger(port.port) && port.port >= 1 && port.port <= 65535 &&
        typeof port.protocol === "string" && typeof port.status === "string" &&
        (port.pid == null || (Number.isInteger(port.pid) && port.pid > 0)) &&
        textFields.every((field) => port[field] == null || typeof port[field] === "string"))) {
    throw new Error("The local dashboard returned an invalid listener snapshot. Rescan to try again.");
  }
  return data;
}

export function terminatePort(port, token) {
  return getJson(`/api/ports/${port.port}/terminate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-PortWatch-Token": token,
    },
    body: JSON.stringify({ pid: port.pid, started_at: port.started_at ?? null }),
  });
}
