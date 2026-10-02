"use strict";

import { element, elements, icon, listenerKey } from "./dashboard-view.js";

export function renderDashboard(ports, allPorts, selectedListener, query) {
  renderListeners(ports, selectedListener);
  renderRoutes(ports, selectedListener);
  renderInspector(allPorts.find((port) => listenerKey(port) === selectedListener) || null);
  elements.portCount.textContent = String(allPorts.length);
  elements.visibleCount.textContent = ports.length === allPorts.length ? "" : `${ports.length} shown`;
  elements.listState.hidden = ports.length > 0;
  elements.listenerList.hidden = ports.length === 0;
  elements.routeState.hidden = ports.length > 0;
  elements.routeList.hidden = ports.length === 0;
  const hasQuery = query.trim().length > 0;
  elements.routeState.querySelector("p").textContent = hasQuery
    ? "No listeners match this search."
    : "No listening routes to show in this range.";
  elements.clearSearch.hidden = !hasQuery;
}

function renderListeners(ports, selectedListener) {
  const fragment = document.createDocumentFragment();
  for (const port of ports) {
    const row = element("li");
    const button = element("button", "listener-row");
    button.type = "button";
    button.dataset.listener = listenerKey(port);
    button.setAttribute("aria-pressed", String(listenerKey(port) === selectedListener));
    button.setAttribute("aria-label", `Port ${port.port}, ${port.process_name || "unknown process"}, ${port.project_name || "project not detected"}`);
    button.append(
      element("span", "listener-port", String(port.port)),
      element("span", "listener-process", port.process_name || "Unknown process"),
      element("span", "listener-project", port.project_name || "—"),
    );
    row.append(button);
    fragment.append(row);
  }
  elements.listenerList.replaceChildren(fragment);
}

function makeRouteNode(primary, secondary, extraClass = "") {
  const node = element("span", `route-node ${extraClass}`.trim());
  node.setAttribute("aria-hidden", "true");
  const lamp = element("span", "route-dot");
  const copy = element("span", "node-copy");
  copy.append(element("span", "node-primary", primary));
  if (secondary) copy.append(element("span", "node-secondary", secondary));
  node.append(lamp, copy);
  return node;
}

function renderRoutes(ports, selectedListener) {
  const fragment = document.createDocumentFragment();
  for (const port of ports) {
    const item = element("li", "route-item");
    const button = element("button", "route-row");
    button.type = "button";
    button.dataset.listener = listenerKey(port);
    button.setAttribute("aria-pressed", String(listenerKey(port) === selectedListener));
    button.setAttribute("aria-label", `Inspect port ${port.port}, process ${port.process_name || "unknown"}, project ${port.project_name || "not detected"}`);
    button.append(
      makeRouteNode(String(port.port), `${port.status === "LISTENING" ? "Listening" : port.status} · ${port.protocol.toUpperCase()}`, "port-value"),
      makeRouteNode(port.process_name || "Unknown process", port.pid ? `PID ${port.pid}` : "PID unavailable"),
      makeRouteNode(port.project_name || "No project detected", port.working_directory || "Directory unavailable"),
    );
    item.append(button);
    fragment.append(item);
  }
  elements.routeList.replaceChildren(fragment);
}

function setFact(node, value) {
  node.textContent = value || "—";
}

function formatStartTime(value) {
  if (!value) return "Unavailable";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "Unavailable" : date.toLocaleString();
}

function renderInspector(port) {
  elements.inspectorState.hidden = Boolean(port);
  elements.listeningTag.hidden = !port;
  elements.inspectorHeading.textContent = port ? `Port ${port.port}` : "Select a port";
  setFact(elements.process, port?.process_name || "Unknown process");
  setFact(elements.pid, port?.pid ? String(port.pid) : "Unavailable");
  setFact(elements.project, port?.project_name || "No project detected");
  setFact(elements.started, formatStartTime(port?.started_at));
  setFact(elements.command, port?.command || "Command unavailable");
  setFact(elements.directory, port?.working_directory || "Directory unavailable");
  elements.copyCommand.disabled = !port?.command;
  elements.copyDirectory.disabled = !port?.working_directory;
  elements.copyCommand.replaceChildren(icon("copy"));
  elements.copyDirectory.replaceChildren(icon("copy"));
  elements.terminate.disabled = !port?.pid;
}
