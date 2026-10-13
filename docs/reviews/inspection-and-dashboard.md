# Inspection and dashboard review

## Starting state

The main branch contained PortWatch 0.1.1 with a working CLI, local dashboard,
Windows bundle workflow, and 136 passing Python tests. The working tree was
clean. The default remote branch was main.

The inspection paths enriched every discovered listener before filtering or
finding an available port. CLI scripts had range filtering and JSON snapshots,
but lacked metadata filters, sorting, CSV, and finite watch sessions. Dashboard
termination checked the port and PID without comparing process start time.

## Changes

Listener text matching lives in a pure shared module and combines with PID,
process, and project filters. Existing commands and JSON snapshot fields remain
available. Sorting and output formatting happen after filtering.

Socket discovery stays TCP-only. Range and inspection queries resolve only the
listeners they need; available-port discovery performs no process enrichment.
Available-port results remain advisory snapshots rather than socket reservations.

Dashboard actions compare the displayed start time with the fresh listener
metadata. Clients sending action requests must include the snapshot's
`started_at` value when it is available. The browser and runtime smoke do so.
The action token and same-origin restrictions remain required.

Malformed snapshots preserve existing browser results. Confirmation submissions
are guarded while an action is pending, and conflict responses trigger a scan
without hiding the explanation. Initial session failures can recover via Rescan.

## Validation

Python regressions exercise command output, filters, sorting, invalid inputs,
process resolution counts, project detection, HTTP parsing, and stale identity.
The JavaScript module harness checks requests and browser state transitions.
The live smoke checks real listeners, packaged static routes, CLI behavior, and
confirmed termination of a child process created solely for the smoke.

Local validation uses Windows and Python 3.12. The repository CI matrix covers
Windows and Linux on Python 3.11, 3.12, and 3.13.
