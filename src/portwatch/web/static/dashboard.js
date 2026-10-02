"use strict";

import { fetchPorts, getJson, parseRange, terminatePort } from "./dashboard-api.js";
import { renderDashboard } from "./dashboard-render.js";
import {
  elements,
  listenerKey,
  setConnection,
  setLastScan,
  setNotice,
} from "./dashboard-view.js";

const state = {
  token: "",
  ports: [],
  selectedListener: null,
  scanning: false,
};

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
  renderDashboard(filterPorts(), state.ports, state.selectedListener, elements.search.value);
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
