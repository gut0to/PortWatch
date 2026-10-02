# Runtime and executable review — 0.1.1

Base: `main` at `8bc2a92850829f7f4a09a93e1569dc085d06e42b`.
Scope: the existing runtime and `git diff main...HEAD`; README is the approved specification.
The repository originally used `feat/portwatch-mvp` as its default branch. Both previous
feature PRs were already merged into that history before `main` was created.

## Standards

Ten findings were evaluated across the initial, final and cross-platform reviews:

- Undefined dashboard confirmation helper: corrected and reproduced with real ES modules.
- Listener identity becoming stale during CLI confirmation: PID and start time are rechecked.
- Permission-denied scans returning false empty results: now explicit domain errors.
- Forced termination timeout escaping: converted into a termination failure.
- Inspection errors contaminating JSON stdout: moved to stderr.
- Exhausted port searches escaping: stable error code and message.
- A still-occupied port reporting successful termination: now failure code 5.
- Smoke cleanup losing children during races: disappearance is tolerated and cleanup is nested.
- Unbounded fixture handshake: now has a ten-second deadline and regression test.
- Linux zombie termination appearing to time out: exited processes awaiting parent reaping
  are now recognized as stopped, with graceful and forced regression cases.

The most consequential operational finding was stale identity before termination. The CLI now
rechecks PID and start time; dashboard actions retain their fresh port/PID validation. A remaining
design opportunity is to share process creation-time validation across both interfaces, reducing
the existing narrow PID-reuse race at the OS boundary.

System-error handling is centralized at the CLI boundary. MIME types for packaged assets are
deterministic. No new documented-standard violations or release blockers remain in the reviewed diff.

## Spec

Seven findings were evaluated: broken dashboard confirmation; permission exit codes;
JSON error output; exhausted port lookup; incomplete termination handling; partial executable
verification; and selection changing while a confirmation is open. Each received a correction
or explicit regression coverage. The confirmation now submits the listener shown in its modal.

The user's exact symptom was a console opening and closing on double-click. The frozen entrypoint
now starts the dashboard without arguments, keeping the server active. Explicit commands still
use the CLI, and source invocation without arguments still lists ports. README documents this.
No scope creep or remaining specification blockers were identified in the final review.

## Validation

- Python unit/HTTP tests with the repository's 100% branch-coverage threshold.
- Linux CI exposed a non-child zombie wait deadlock in the real HTTP smoke; the correction
  is verified by repeating the original CI smoke on Python 3.11–3.13.
- Ruff lint and formatting; strict Mypy checks.
- Two JavaScript module regressions, including confirmation during selection changes.
- Source and Windows executable smoke tests from an unrelated working directory.
- Real listener discovery, inspect/next, packaged HTTP assets and authenticated termination
  of a disposable child process; smoke tests never open a browser.
- Frozen no-argument routing is tested with a mocked application; an actual browser UI was not opened.

The global Python was 3.10 and unsupported. `run.ps1` selects the supported `.venv` explicitly.
The original executable was locked; the verified local build is in `dist/release-0.1.1`.
