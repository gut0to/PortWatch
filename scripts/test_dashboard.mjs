import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

// Execute the actual ES modules with a small DOM seam; no browser is required.
async function dashboard(options = {}) {
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
  const configuration = options;
  const requests = [];
  let ports = [{ port: 3000, pid: 42, process_name: "python", protocol: "tcp", status: "LISTENING" }];
  const context = vm.createContext({
    document, HTMLElement: Node, console, AbortController,
    setTimeout: configuration.setTimeout || setTimeout,
    clearTimeout: configuration.clearTimeout || clearTimeout,
    fetch: async (url, options) => {
      requests.push({ url, options });
      if (configuration.respond) {
        const response = await configuration.respond(url, options);
        if (response) return response;
      }
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
  return { nodes, requests, api: modules.get("dashboard-api.js").namespace, view: modules.get("dashboard-view.js").namespace, setPorts(value) { ports = value; } };
}

test("confirmation opens for the selected listener and submits its PID", async () => {
  const { nodes, requests } = await dashboard();
  nodes.get("#terminate").listeners.click();
  assert.equal(nodes.get("#confirm-dialog").open, true);
  assert.equal(nodes.get("#confirm-pid").textContent, "42");
  nodes.get("#confirm-form").listeners.submit({ preventDefault() {} });
  await new Promise(setImmediate);
  const request = requests.find(({ url }) => url.includes("terminate"));
  assert.deepEqual(JSON.parse(request.options.body), { pid: 42, started_at: null });
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
  assert.deepEqual(JSON.parse(request.options.body), { pid: 42, started_at: null });
});


test("action requests preserve both JSON accept and authorization headers", async () => {
  const { api, requests } = await dashboard();
  await api.terminatePort({ port: 3000, pid: 42 }, "token");
  const headers = requests.at(-1).options.headers;
  assert.equal(headers.Accept, "application/json");
  assert.equal(headers["X-PortWatch-Token"], "token");
});


test("malformed snapshots keep the previous listener results", async () => {
  const { nodes, setPorts } = await dashboard();
  setPorts([{ port: "wrong", protocol: null }]);
  await nodes.get("#rescan").listeners.click();
  assert.equal(nodes.get("#port-count").textContent, "1");
  assert.match(nodes.get("#notice").textContent, /invalid listener snapshot/);
});


test("range inputs reject exponents decimals and whitespace", async () => {
  const { api, nodes } = await dashboard();
  for (const value of ["1e3", "1.0", " 1", "", "0x10"]) {
    nodes.get("#range-start").value = value;
    assert.throws(() => api.parseRange({ rangeStart: nodes.get("#range-start"), rangeEnd: nodes.get("#range-end") }));
  }
});


test("listener keys distinguish reused process IDs", async () => {
  const { view } = await dashboard();
  const item = { port: 3000, pid: 42, process_name: "python" };
  assert.notEqual(view.listenerKey({ ...item, started_at: "2026-01-01" }), view.listenerKey({ ...item, started_at: "2026-01-02" }));
});


test("repeated confirmation submissions send one stop request", async () => {
  const { nodes, requests } = await dashboard();
  nodes.get("#terminate").listeners.click();
  const submit = nodes.get("#confirm-form").listeners.submit;
  submit({ preventDefault() {} });
  submit({ preventDefault() {} });
  await new Promise(setImmediate);
  assert.equal(requests.filter(({ url }) => url.includes("terminate")).length, 1);
});


test("successful termination remains visible after refreshing listeners", async () => {
  const { nodes } = await dashboard();
  nodes.get("#terminate").listeners.click();
  nodes.get("#confirm-form").listeners.submit({ preventDefault() {} });
  await new Promise(setImmediate);
  assert.equal(nodes.get("#notice").textContent, "Stopped.");
});


test("rescan recovers from an initial session failure", async () => {
  let sessions = 0;
  const { nodes } = await dashboard({ respond(url) {
    if (url === "/api/session" && ++sessions === 1) throw new Error("temporarily unavailable");
  }});
  assert.match(nodes.get("#notice").textContent, /temporarily unavailable/);
  await nodes.get("#rescan").listeners.click();
  assert.equal(sessions, 2);
  assert.equal(nodes.get("#port-count").textContent, "1");
});


test("termination confirmation stays closed while a scan is pending", async () => {
  let resolveScan;
  let block = false;
  const { nodes } = await dashboard({ respond(url) {
    if (block && url.startsWith("/api/ports")) return new Promise((resolve) => { resolveScan = resolve; });
  }});
  block = true;
  const pending = nodes.get("#rescan").listeners.click();
  nodes.get("#terminate").listeners.click();
  assert.notEqual(nodes.get("#confirm-dialog").open, true);
  resolveScan({ ok: true, json: async () => ({ ports: [], scanned_at: "2026-01-01" }) });
  await pending;
});

test("stale termination refreshes listeners and retains the conflict explanation", async () => {
  const { nodes, requests } = await dashboard({ respond(url) {
    if (url.includes("terminate")) return {
      ok: false, status: 409, json: async () => ({ error: "Listener identity no longer matches." }),
    };
  }});
  nodes.get("#terminate").listeners.click();
  nodes.get("#confirm-form").listeners.submit({ preventDefault() {} });
  await new Promise(setImmediate);
  assert.equal(requests.filter(({ url }) => url.startsWith("/api/ports?")).length, 2);
  assert.equal(nodes.get("#notice").textContent, "Listener identity no longer matches.");
});

test("HTTP errors with null JSON bodies still explain their status", async () => {
  const { api } = await dashboard({ respond(url) {
    if (url === "/failure") return { ok: false, status: 503, json: async () => null };
  }});
  await assert.rejects(api.getJson("/failure"), /Request failed \(503\)/);
});


test("dashboard requests time out and always release their timer", async () => {
  let timeout;
  let cleared = 0;
  const { api } = await dashboard({
    setTimeout(callback) { timeout = callback; return 1; },
    clearTimeout() { cleared += 1; },
    respond(url, options) {
      if (url === "/slow") return new Promise((resolve, reject) => {
        options.signal.addEventListener("abort", () => reject(new Error("aborted")));
      });
    },
  });
  const pending = api.getJson("/slow");
  timeout();
  await assert.rejects(pending, /15 seconds/);
  assert.ok(cleared >= 3);
});


test("expired action sessions recover without retrying termination", async () => {
  let stops = 0;
  const { nodes, requests } = await dashboard({ respond(url) {
    if (url.includes("terminate")) {
      stops += 1;
      return { ok: false, status: 403, json: async () => ({ error: "Confirm the action again." }) };
    }
  }});
  nodes.get("#terminate").listeners.click();
  nodes.get("#confirm-form").listeners.submit({ preventDefault() {} });
  await new Promise(setImmediate);
  assert.equal(stops, 1);
  assert.equal(requests.filter(({url}) => url === "/api/session").length, 2);
  assert.equal(nodes.get("#notice").textContent, "Confirm the action again.");
});


test("listener selection keys cannot collide through metadata delimiters", async () => {
  const { view } = await dashboard();
  const first = {port: 3000, pid: 42, protocol: "tcp", process_name: "a:b", started_at: "c"};
  const second = {...first, process_name: "a", started_at: "b:c"};
  assert.notEqual(view.listenerKey(first), view.listenerKey(second));
  assert.equal(view.listenerKey(first), view.listenerKey({...first, process_name: "updated"}));
});
