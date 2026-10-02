# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

User-chosen: HTML, CSS, and JavaScript served locally by the existing Python application.

## Users

Developers working on their own Windows or Linux machine who need to find which process is using a local TCP port.

## Product Purpose

PortWatch helps developers inspect listening ports, understand the process and project behind each listener, find an available port, watch changes, and free a port. Success means answering “what is using this port?” and acting safely without memorizing platform-specific network commands.

## Positioning

PortWatch combines local TCP socket inspection with process details and project-root detection in one account-free tool. It stays on the developer's machine and can be used from the existing CLI or a local browser dashboard.

## Operating Context

The primary workflow happens on the same machine where development servers and other local services are running. The dashboard is served by PortWatch on loopback and reads live listener information. Developers may refresh or watch the list, inspect a listener, and request termination after reviewing a confirmation.

## Capabilities and Constraints

- The existing CLI supports `list`, `inspect`, `next`, `kill`, `free`, and `watch`, including JSON output for supported commands.
- The current network scanner discovers listening TCP ports; UDP support is planned, not available.
- Process termination can be graceful or forced and must remain an explicit, confirmed user action in the dashboard.
- The project requires Python 3.11 or newer and supports Windows and Linux.
- PortWatch is local-first, sends no telemetry, and requires no account.
- The user selected plain HTML, CSS, and JavaScript served by the Python application. No frontend framework or external deployment target is required.

## Brand Commitments

Use the existing PortWatch name and the concise, practical voice established by the README and CLI. The existing CLI remains available.

## Evidence on Hand

The repository contains a working CLI, port and process services, project detection, JSON serializers, and tests for the current behavior. No visual dashboard, customer evidence, or marketing claims are present; do not invent any.

## Product Principles

- Show the local state that helps answer who owns a port.
- Keep inspection and process termination distinct; require a deliberate confirmation before termination.
- Keep the tool local, account-free, and useful from the terminal as well as the browser.
- Prefer live machine data and clearly label unavailable process details.
