"use strict";

export function searchListeners(ports, query) {
  const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return ports.filter((port) => {
    const values = [port.port, port.pid, port.protocol, port.status, port.process_name,
      port.project_name, port.command, port.working_directory]
      .filter((value) => value != null).map((value) => String(value).toLowerCase());
    return terms.every((term) => term.startsWith("-") && term.length > 1
      ? !values.some((value) => value.includes(term.slice(1)))
      : values.some((value) => value.includes(term)));
  });
}
