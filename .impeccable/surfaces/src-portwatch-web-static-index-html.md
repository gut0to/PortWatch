---
version: 1
slug: "src-portwatch-web-static-index-html"
primary_target: "src/portwatch/web/static/index.html"
related_targets: ["src/portwatch/web/server.py"]
---

# PortWatch local dashboard

Mode: operate. Audience: developers finding which local TCP listener owns a port.
Task: filter listeners, follow the selected port to its process and detected project, inspect details, or deliberately terminate that process.
Evidence and constraints: use live scanner output only; there are no seeded rows, claims, telemetry, account, or inferred free/busy health states. Preserve the existing CLI and bundle the static UI in the executable.
Approved composition: `.impeccable/mocks/signal-routes.png`.

## Direction contract

**THESIS:** Each selected listener becomes one traceable route from TCP port to owning process to detected project. The surface refuses disconnected KPI cards and inferred health states.

**OWN-WORLD:** Deep ink-navy panels, chalk lettering, fine engineering rules, and exact flat route geometry evoke an enamel signal board. Use signal color only for the selected route and pair every listener status with the literal “Listening · TCP” label. Use a compact sans-serif for controls and tabular numerals for ports and PIDs.

**STORY:** A developer scans the current machine, filters by port, process, or project, selects a listener, checks its PID, command, working directory, and detected project, then may terminate it after a clear confirmation.

**FIRST VIEWPORT:** A 44px PortWatch masthead and localhost state sit above a slim scan, search, TCP range, and rescan strip. Below, a narrow listener selector occupies about 20%, the Port → Process → Project route field about 55%, and the selected-listener inspector about 25%. The selected route is highlighted; other connections stay neutral. At narrow widths, stack the full-width selector, route diagram, then inspector without hiding or shrinking critical labels.

**FORM:** Signal Interlocking, assigned form 4 of the ranked direction list, seed `61a4df85`; the user approved the Route field composition at `.impeccable/mocks/signal-routes.png`. The interface is a local browser dashboard served by the Python CLI and bundled for Windows.

**FINISH:** unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
