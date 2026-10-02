import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

// Execute the actual ES modules with a small DOM seam; no browser is required.
async function dashboard() {
  const nodes = new Map();
  class Node {
    constructor() {
      this.dataset = {};
      this.listeners = {};
      this.value = "";
      this.textContent = "";
    }
    setAttribute() {}
    removeAttribute() {}
    append() {}
    replaceChildren() {}
    querySelector() { return new Node(); }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    showModal() { this.open = true; }
    close() { this.open = false; }
    focus() {}
  }
  const document = {
    querySelector(selector) {
      if (!nodes.has(selector)) nodes.set(selector, new Node());
      return nodes.get(selector);
    },
    createElement: () => new Node(),
    createElementNS: () => new Node(),
    createDocumentFragment: () => new Node(),
    addEventListener() {},
  };
  document.querySelector("#range-start").value = "1";
  document.querySelector("#range-end").value = "65535";
  const requests = [];
  let ports = [{ port: 3000, pid: 42, process_name: "python", protocol: "tcp", status: "LISTENING" }];
  const context = vm.createContext({
    document, HTMLElement: Node, console,
    fetch: async (url, options) => {
      requests.push({ url, options });
      const data = url === "/api/session"
        ? { token: "a".repeat(43) }
        : url.includes("terminate") ? { message: "Stopped." }
        : { ports, scanned_at: "2026-10-02T12:00:00Z" };
      return { ok: true, json: async () => data };
    },
  });
  const modules = new Map();
  async function load(name) {
    if (!modules.has(name)) {
      const source = await readFile(new URL(`../src/portwatch/web/static/${name}`, import.meta.url), "utf8");
      modules.set(name, new vm.SourceTextModule(source, { context, identifier: name }));
    }
    return modules.get(name);
  }
  const root = await load("dashboard.js");
  await root.link((specifier) => load(specifier.replace("./", "")));
  await root.evaluate();
  await new Promise(setImmediate);
  return { nodes, requests, setPorts(value) { ports = value; } };
}

test("confirmation opens for the selected listener and submits its PID", async () => {
  const { nodes, requests } = await dashboard();
  nodes.get("#terminate").listeners.click();
  assert.equal(nodes.get("#confirm-dialog").open, true);
  assert.equal(nodes.get("#confirm-pid").textContent, "42");
  nodes.get("#confirm-form").listeners.submit({ preventDefault() {} });
  await new Promise(setImmediate);
  const request = requests.find(({ url }) => url.includes("terminate"));
  assert.deepEqual(JSON.parse(request.options.body), { pid: 42 });
});

test("confirmation retains its displayed listener when a scan changes selection", async () => {
  const { nodes, requests, setPorts } = await dashboard();
  nodes.get("#terminate").listeners.click();
  setPorts([{ port: 4000, pid: 99, process_name: "node", protocol: "tcp", status: "LISTENING" }]);
  await nodes.get("#rescan").listeners.click();
  assert.equal(nodes.get("#confirm-pid").textContent, "42");
  nodes.get("#confirm-form").listeners.submit({ preventDefault() {} });
  await new Promise(setImmediate);
  const request = requests.find(({ url }) => url.includes("terminate"));
  assert.equal(request.url, "/api/ports/3000/terminate");
  assert.deepEqual(JSON.parse(request.options.body), { pid: 42 });
});
