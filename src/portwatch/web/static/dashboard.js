"use strict";

import { fetchPorts, getJson, parseRange, terminatePort } from "./dashboard-api.js";

const state = {
  token: "",
  ports: [],
  selectedListener: null,
  scanning: false,
};

const elements = {
  connection: document.querySelector("#connection-state"),
  connectionLabel: document.querySelector("#connection-label"),
  scanValue: document.querySelector("#scan-value"),
  search: document.querySelector("#search"),
  rangeForm: document.querySelector("#range-form"),
  rangeStart: document.querySelector("#range-start"),
  rangeEnd: document.querySelector("#range-end"),
  rescan: document.querySelector("#rescan"),
  emptyRescan: document.querySelector("#empty-rescan"),
  clearSearch: document.querySelector("#clear-search"),
  listenerList: document.querySelector("#listener-list"),
  routeList: document.querySelector("#route-list"),
  listState: document.querySelector("#list-state"),
  routeState: document.querySelector("#route-state"),
  portCount: document.querySelector("#port-count"),
  visibleCount: document.querySelector("#visible-count"),
  summary: document.querySelector("#summary"),
  notice: document.querySelector("#notice"),
  inspectorHeading: document.querySelector("#inspector-heading"),
  listeningTag: document.querySelector("#listening-tag"),
  inspectorState: document.querySelector("#inspector-state"),
  process: document.querySelector("#fact-process"),
  pid: document.querySelector("#fact-pid"),
  project: document.querySelector("#fact-project"),
  started: document.querySelector("#fact-started"),
  command: document.querySelector("#fact-command"),
  directory: document.querySelector("#fact-directory"),
  copyCommand: document.querySelector("#copy-command"),
  copyDirectory: document.querySelector("#copy-directory"),
  terminate: document.querySelector("#terminate"),
  dialog: document.querySelector("#confirm-dialog"),
  confirmForm: document.querySelector("#confirm-form"),
  cancelTerminate: document.querySelector("#cancel-terminate"),
  confirmTerminate: document.querySelector("#confirm-terminate"),
  confirmProcess: document.querySelector("#confirm-process"),
  confirmPid: document.querySelector("#confirm-pid"),
  confirmPort: document.querySelector("#confirm-port"),
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function listenerKey(port) {
  return `${port.port}:${port.pid ?? "unknown"}:${port.process_name ?? ""}`;
}

function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 20 20");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", name === "copy" ? "M7 6V4h9v10h-2M4 8h9v9H4z" : "M6 5l4 5-4 5m6 0h4");
  svg.append(path);
  return svg;
}

function setConnection(label, hasError = false) {
  elements.connection.dataset.state = hasError ? "error" : "online";
  elements.connectionLabel.textContent = label;
}

function setNotice(message, tone = "info") {
  elements.notice.textContent = message;
  elements.notice.dataset.tone = tone;
  elements.notice.hidden = !message;
}

function setLastScan(value) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    elements.scanValue.textContent = "Time unavailable";
    elements.scanValue.removeAttribute("datetime");
    return;
  }
  elements.scanValue.dateTime = date.toISOString();
  elements.scanValue.textContent = date.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

async function scan() {
  if (state.scanning) return;
  let range;
  try {
    range = parseRange(elements);
  } catch (error) {
    setNotice(error.message, "error");
    return;
  }

  state.scanning = true;
  elements.rescan.disabled = true;
  elements.rangeStart.disabled = true;
  elements.rangeEnd.disabled = true;
  elements.emptyRescan.disabled = true;
  elements.rescan.setAttribute("aria-busy", "true");
  elements.rescan.querySelector("span").textContent = "Scanning…";
  elements.summary.textContent = "Scanning local TCP listeners…";
  setNotice("");

  try {
    const result = await fetchPorts(range);
    state.ports = Array.isArray(result.ports) ? result.ports : [];
    state.ports.sort((left, right) => left.port - right.port);
    const visible = filterPorts();
    if (!visible.some((port) => listenerKey(port) === state.selectedListener)) {
      state.selectedListener = visible[0] ? listenerKey(visible[0]) : null;
    }
    setLastScan(result.scanned_at);
    setConnection("localhost · connected");
    render();
    elements.summary.textContent = `${state.ports.length} listening TCP ${state.ports.length === 1 ? "port" : "ports"} found.`;
  } catch (error) {
    setConnection("Local scan unavailable", true);
    elements.summary.textContent = state.ports.length
      ? "Last scan failed; showing the previous results."
      : "The first scan could not be completed.";
    setNotice(error.message || "PortWatch could not scan this machine.", "error");
    render();
  } finally {
    state.scanning = false;
    elements.rescan.disabled = false;
    elements.rangeStart.disabled = false;
    elements.rangeEnd.disabled = false;
    elements.emptyRescan.disabled = false;
    elements.rescan.removeAttribute("aria-busy");
    elements.rescan.querySelector("span").textContent = "Rescan";
  }
}

function filterPorts() {
  const query = elements.search.value.trim().toLocaleLowerCase();
  if (!query) return state.ports;
  return state.ports.filter((port) => {
    const values = [
      port.port,
      port.protocol,
      port.status,
      port.process_name,
      port.pid,
      port.project_name,
      port.command,
      port.working_directory,
    ];
    return values.some((value) => value !== null && value !== undefined && String(value).toLocaleLowerCase().includes(query));
  });
}

function render() {
  const ports = filterPorts();
  renderListeners(ports);
  renderRoutes(ports);
  renderInspector(state.ports.find((port) => listenerKey(port) === state.selectedListener) || null);
  elements.portCount.textContent = String(state.ports.length);
  elements.visibleCount.textContent = ports.length === state.ports.length ? "" : `${ports.length} shown`;
  elements.listState.hidden = ports.length > 0;
  elements.listenerList.hidden = ports.length === 0;
  elements.routeState.hidden = ports.length > 0;
  elements.routeList.hidden = ports.length === 0;
  const hasQuery = elements.search.value.trim().length > 0;
  elements.routeState.querySelector("p").textContent = hasQuery
    ? "No listeners match this search."
    : "No listening routes to show in this range.";
  elements.clearSearch.hidden = !hasQuery;
}

function renderListeners(ports) {
  const fragment = document.createDocumentFragment();
  for (const port of ports) {
    const row = element("li");
    const button = element("button", "listener-row");
    button.type = "button";
    button.dataset.listener = listenerKey(port);
    button.setAttribute("aria-pressed", String(listenerKey(port) === state.selectedListener));
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

function renderRoutes(ports) {
  const fragment = document.createDocumentFragment();
  for (const port of ports) {
    const item = element("li", "route-item");
    const button = element("button", "route-row");
    button.type = "button";
    button.dataset.listener = listenerKey(port);
    button.setAttribute("aria-pressed", String(listenerKey(port) === state.selectedListener));
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

function selectPort(key) {
  const port = state.ports.find((item) => listenerKey(item) === key);
  if (!port) return;
  state.selectedListener = key;
  render();
}

function readClickedPort(event) {
  const button = event.target.closest("button[data-listener]");
  if (!button) return;
  selectPort(button.dataset.listener);
}

async function copyValue(value, label) {
  try {
    await navigator.clipboard.writeText(value);
    setNotice(`${label} copied.`, "success");
  } catch {
    setNotice(`Could not copy ${label.toLocaleLowerCase()}. Select the text and copy it manually.`, "error");
  }
}

function openConfirmation() {
  const port = state.ports.find((item) => listenerKey(item) === state.selectedListener);
  if (!port?.pid) return;
  setFact(elements.confirmProcess, port.process_name || "Unknown process");
  setFact(elements.confirmPid, String(port.pid));
  setFact(elements.confirmPort, String(port.port));
  elements.dialog.showModal();
}

async function terminateSelected() {
  const port = state.ports.find((item) => listenerKey(item) === state.selectedListener);
  if (!port?.pid || !state.token) return;
  elements.confirmTerminate.disabled = true;
  elements.confirmTerminate.textContent = "Stopping…";
  try {
    const result = await terminatePort(port, state.token);
    elements.dialog.close();
    setNotice(result.message || "Termination request sent.", "success");
    await scan();
  } catch (error) {
    elements.dialog.close();
    setNotice(error.message || "The process could not be stopped.", "error");
    if (error.message.includes("changed") || error.message.includes("available")) await scan();
  } finally {
    elements.confirmTerminate.disabled = false;
    elements.confirmTerminate.textContent = "Stop process";
  }
}

elements.listenerList.addEventListener("click", readClickedPort);
elements.routeList.addEventListener("click", readClickedPort);
elements.rescan.addEventListener("click", scan);
elements.emptyRescan.addEventListener("click", scan);
elements.rangeForm.addEventListener("submit", (event) => {
  event.preventDefault();
  scan();
});
elements.search.addEventListener("input", () => {
  const visible = filterPorts();
  if (!visible.some((port) => listenerKey(port) === state.selectedListener)) {
    state.selectedListener = visible[0] ? listenerKey(visible[0]) : null;
  }
  render();
});
elements.clearSearch.addEventListener("click", () => {
  elements.search.value = "";
  elements.search.focus();
  state.selectedListener = state.ports[0] ? listenerKey(state.ports[0]) : null;
  render();
});
elements.terminate.addEventListener("click", openConfirmation);
elements.cancelTerminate.addEventListener("click", () => elements.dialog.close());
elements.confirmForm.addEventListener("submit", (event) => {
  event.preventDefault();
  terminateSelected();
});
elements.copyCommand.addEventListener("click", () => {
  const port = state.ports.find((item) => listenerKey(item) === state.selectedListener);
  if (port?.command) copyValue(port.command, "Command");
});
elements.copyDirectory.addEventListener("click", () => {
  const port = state.ports.find((item) => listenerKey(item) === state.selectedListener);
  if (port?.working_directory) copyValue(port.working_directory, "Working directory");
});

document.addEventListener("keydown", (event) => {
  const target = event.target;
  const inEditable = target instanceof HTMLElement && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
  if (elements.dialog.open) return;
  if (event.key === "/" && !inEditable && !event.altKey && !event.ctrlKey && !event.metaKey) {
    event.preventDefault();
    elements.search.focus();
  }
  if (event.key.toLocaleLowerCase() === "r" && !inEditable && !event.altKey && !event.ctrlKey && !event.metaKey) {
    scan();
  }
});

async function start() {
  try {
    const session = await getJson("/api/session");
    if (typeof session.token !== "string" || session.token.length < 32) {
      throw new Error("The local action token could not be created.");
    }
    state.token = session.token;
    setConnection("localhost · connected");
    await scan();
  } catch (error) {
    setConnection("Local scan unavailable", true);
    setNotice(error.message || "Start the PortWatch dashboard again to reconnect.", "error");
    elements.summary.textContent = "The local dashboard could not connect to the scanner.";
  }
}

start();
