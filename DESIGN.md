---
name: PortWatch
description: A local signal board that traces TCP listeners to their processes and projects.
colors:
  ink: "#081827"
  surface: "#0a1b29"
  surface-raised: "#0e2232"
  surface-selected: "#10283a"
  line: "#1e3a52"
  line-strong: "#31536c"
  chalk: "#f1f3f3"
  muted: "#b1c6d8"
  quiet: "#91a9bd"
  signal-green: "#1df682"
  signal-red: "#ff625b"
  signal-amber: "#ffc36a"
  focus: "#a0ffca"
typography:
  brand:
    fontFamily: '"Amaranth", "Segoe UI", Arial, sans-serif'
    fontSize: "44px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "-0.035em"
  heading:
    fontFamily: '"Martel Sans", "Segoe UI", Arial, sans-serif'
    fontSize: "23px"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: '"Segoe UI", "Noto Sans", Arial, sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  data:
    fontFamily: '"Cascadia Code", Consolas, ui-monospace, monospace'
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  xs: "6px"
  sm: "8px"
  md: "9px"
  lg: "12px"
  dialog: "14px"
  pill: "999px"
spacing:
  1: "0.35rem"
  2: "0.65rem"
  3: "0.9rem"
  4: "1.1rem"
  5: "1.45rem"
  6: "1.8rem"
  7: "2.35rem"
components:
  search-field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.chalk}"
    rounded: "{rounded.md}"
    padding: "0 12px"
    height: "44px"
  route-node:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.chalk}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  selected-route:
    backgroundColor: "#0e2432"
    textColor: "{colors.chalk}"
    rounded: "{rounded.md}"
  listening-tag:
    textColor: "#b8ffd7"
    rounded: "{rounded.pill}"
    padding: "3px 8px"
  terminate-button:
    backgroundColor: "#251b22"
    textColor: "#ffaaa3"
    rounded: "{rounded.sm}"
    padding: "0 14px"
    height: "42px"
  confirmation-dialog:
    backgroundColor: "#0b1e2c"
    textColor: "{colors.chalk}"
    rounded: "{rounded.dialog}"
    padding: "25px"
---

# Design System: PortWatch

## Overview

**Creative North Star: "Signal Interlocking"**

PortWatch presents each live TCP listener as a route with a visible owner. Ink-navy surfaces, chalk text, fine blue rules, and aligned data make the board feel like an enamel signal panel built for inspection. The approved route-field composition is the visual center: Port → Process → Project remains one connected reading path.

The interface stays compact and factual. Green marks the selected route and appears alongside the literal listening status; red identifies errors and termination. The product reports local scan results and process details, so visual status never implies availability or health beyond the scanner's reported state. Termination stays a separate action with a confirmation that repeats the process, PID, and port.

**Key Characteristics:**
- Deep ink-navy surfaces with chalk text and fine blue dividers.
- A connected three-step route field for port ownership.
- Compact sans-serif controls and tabular monospace values.
- Explicit local connection, listening, and termination states.

## Colors

The palette uses cool navy surfaces, pale blue-gray supporting text, and a bright green signal against restrained red error and destructive states.

### Primary
- **Signal Green** (`{colors.signal-green}`): Selected route nodes, route connectors, focus-within search border, and the local connection lamp. The listening tag also pairs green with the explicit “Listening · TCP” label.

### Secondary
- **Signal Red** (`{colors.signal-red}`): Connection errors, invalid port ranges, and the destructive termination action and confirmation.

### Tertiary
- **Signal Amber** (`{colors.signal-amber}`): Reserved in the token set; current interface styles do not assign it to a visible component.

### Neutral
- **Ink Navy** (`{colors.ink}`): Page background and high-contrast text selection foreground.
- **Deep Surface** (`{colors.surface}`): Panels, route nodes' surrounding field, and form backgrounds.
- **Raised Surface** (`{colors.surface-raised}`): Route nodes, notices, and focused search background.
- **Selected Surface** (`{colors.surface-selected}`): Selected listener row.
- **Engineering Line** (`{colors.line}`) and **Strong Line** (`{colors.line-strong}`): Panel divisions, borders, connectors, and control outlines.
- **Chalk** (`{colors.chalk}`): Main text and primary data values.
- **Muted Blue Gray** (`{colors.muted}`) and **Quiet Blue Gray** (`{colors.quiet}`): Labels, secondary values, placeholders, and unselected route markers.
- **Focus Mint** (`{colors.focus}`): Visible keyboard focus outline.

**The Factual Signal Rule.** Pair colored status with literal text. The board reports a listener as “Listening · TCP”; it does not infer a free port or process health.

## Typography

**Display Font:** Amaranth (with Segoe UI and Arial fallbacks; declared for the wordmark and confirmation title)
**Body Font:** Segoe UI (with Noto Sans and Arial fallbacks)
**Label/Mono Font:** Cascadia Code (with Consolas and ui-monospace fallbacks)

**Character:** Compact sans-serif text keeps controls and labels direct. Monospace values make ports, PIDs, scan times, commands, and directories easier to compare. The CSS declares Amaranth and Martel Sans stacks for display accents and headings; the source does not bundle font files, so actual rendering depends on locally available fonts and browser fallback.

### Hierarchy
- **Brand** (400, 44px, line-height 1): PortWatch wordmark; scales to 34px at narrow widths.
- **Headline** (700, 23px, line-height 1.2): Route field and inspector headings; the route title scales to 19px on narrow screens.
- **Title** (650, 23px, line-height 1.2): Panel headings, with responsive panel headings at 17px.
- **Body** (400, 15px, line-height 1.5): Default copy, process details, and controls; body defaults to 14px below 760px.
- **Label** (600–650, 12–13px, 0.035em for uppercase column labels): Supporting metadata and compact field labels.
- **Data** (400, 12–16px, tabular numerals where numeric): Ports, PIDs, timestamps, commands, and directories.

**The Tabular Data Rule.** Keep port and PID values in the monospace stack with tabular numerals so adjacent records scan consistently.

## Layout

The desktop workspace uses three adjacent regions: listener selector, route field, and process inspector. Its nominal proportions are 20:55:23, with minimum widths of 238px, 500px, and 300px; the overall shell caps at 1920px and uses 16px side padding. The masthead and service strip span above the workspace. Panels use 10px gaps, with a minimum workspace height of 560px or 74vh.

At 1240px and below, the selector and route field remain in two columns and the inspector moves to a full-width second row. At 760px and below, the service controls and workspace stack; the listener list comes first, the route field second, and the inspector third. The listener panel is 250–390px tall, the route panel has a 400px minimum, and the inspector has a 380px minimum. At 390px and below, list and route gaps tighten further and the footer stacks vertically. Reduced-motion preferences shorten transitions and disable route-draw animation.

The browser review used a 421×495 viewport, but `.impeccable/review/desktop.png` is absent and the reviewer requested a recapture. Responsive rules above are therefore recorded from CSS; this pass does not claim visual verification of the desktop composition.

## Elevation & Depth

Depth comes from tonal navy layers, crisp borders, route connectors, and restrained shadows. The three main panels use a low ambient shadow (`0 14px 32px rgb(0 0 0 / 10%)`); the confirmation dialog uses a stronger overlay shadow (`0 22px 60px rgb(0 0 0 / 52%)`) over a darkened backdrop. Route geometry and surface shifts carry the hierarchy inside the workspace.

### Shadow Vocabulary
- **Panel lift** (`0 14px 32px rgb(0 0 0 / 10%)`): Separates each main panel from the ink page.
- **Dialog lift** (`0 22px 60px rgb(0 0 0 / 52%)`): Separates the confirmation surface from its dimmed backdrop.

## Shapes

Panels have gently rounded corners (12px) and fine one-pixel borders. Controls and route nodes use compact rounded rectangles (7–9px); the listening status uses a full pill silhouette (999px). Lines and connectors stay straight and precise, with small circular route lamps. Text fields preserve long commands and paths through wrapping or internal scrolling.

## Components

### Buttons
- **Character:** Compact, direct controls with a clear state color.
- **Rescan:** Blue outlined surface, chalk label, 42px minimum height, and green border on hover.
- **Terminate:** Full-width, left-aligned muted red control; hover increases red contrast. It stays disabled until a selected process has a PID.
- **Confirmation:** Red confirm action beside a quiet “Keep process” action. Submission is only available through the confirmation dialog.
- **Focus:** Keyboard focus uses a mint 2px outline with 3px offset.

### Chips
- **Listening tag:** Green text and border on a dark surface, with a small signal lamp and literal “Listening · TCP” copy.

### Cards / Containers
- **Panels:** Listener, route, and inspector regions share the dark surface, 12px radius, fine border, and low shadow.
- **Route nodes:** Raised navy rectangles with a strong blue outline; selected route nodes shift toward green-tinted surfaces and borders.
- **Internal spacing:** Panel headings use 16px side inset; inspector uses 18px padding on desktop and 15px on narrow screens.

### Inputs / Fields
- **Search:** 44px high, dark field with a 9px radius and strong blue outline. Focus-within shifts the border green and background to the raised surface.
- **TCP range:** Number fields use 42px height, 8px radius, and monospace tabular numerals. Invalid bounds receive a red border.
- **Command and directory:** Read-only looking data blocks use a darker inset surface, monospace text, and wrapping or local scrolling; adjacent copy controls stay visually quiet.

### Navigation
- **Selection:** Listener rows and route rows are buttons with explicit pressed state. Hover raises the background slightly; selecting a route highlights its three nodes and connecting rails.
- **Responsive behavior:** Keep the same listener → route → inspector sequence when the workspace stacks at 760px.

### Route Field
- **Structure:** Three aligned nodes carry port/status, process/PID, and project/directory. Fine horizontal rails and arrow tips connect each step.
- **Selected state:** Green connector, lamps, and node outlines trace the active selection. Other routes remain neutral.
- **Behavior:** The route rows are selectable buttons; their accessible names repeat the port and owner details.

### Confirmation Dialog
- **Form:** A centered dark dialog with a 14px radius, dimmed backdrop, and process, PID, and port facts.
- **Actions:** “Keep process” closes the dialog; “Stop process” submits the termination request. Keep the destructive action visually distinct from scan controls.

## Do's and Don'ts

### Do:
- **Do** show listener ownership as one Port → Process → Project route.
- **Do** use live scanner data and label unavailable process details explicitly.
- **Do** pair colored status with the literal status text.
- **Do** keep termination behind a confirmation that identifies the selected process, PID, and port.
- **Do** preserve the listener, route, inspector order as the layout stacks.

### Don't:
- **Don't** imply a port is free, healthy, or blocked unless the scanner reports that fact.
- **Don't** turn the workspace into disconnected summary cards or hide the owner relationship.
- **Don't** encode status by color alone.
- **Don't** reduce critical labels or route content below readable sizes when adapting the layout.
