"use strict";

export const elements = {
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

export function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function listenerKey(port) {
  return `${port.port}:${port.pid ?? "unknown"}:${port.process_name ?? ""}`;
}

export function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 20 20");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", name === "copy" ? "M7 6V4h9v10h-2M4 8h9v9H4z" : "M6 5l4 5-4 5m6 0h4");
  svg.append(path);
  return svg;
}

export function setConnection(label, hasError = false) {
  elements.connection.dataset.state = hasError ? "error" : "online";
  elements.connectionLabel.textContent = label;
}

export function setNotice(message, tone = "info") {
  elements.notice.textContent = message;
  elements.notice.dataset.tone = tone;
  elements.notice.hidden = !message;
}

export function setLastScan(value) {
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
