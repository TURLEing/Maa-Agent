# Using Maa-Agent

Read README.md first. Use the local virtual environment and CLI JSON interface.
No model provider credentials are required by this project.

1. Observe the game and establish the current account before planning a battle.
2. Before choosing a team, follow docs/onboarding.md to create a complete roster.
   Never assume an absent record means an operator is unowned. Unknown skills,
   masteries and modules stay unknown. Do not reuse a roster after switching accounts.
3. Resolve the game's display stage code to its internal ID using installed MAA
   stage resources. PRTS levelKeyword expects that ID: invalid filters may return
   all stages. Validate every candidate's stage_name. Download full actions from
   get/<id>; query results alone are not executable battle scripts.
4. Read author notes, difficulty, skill/module requirements and team ownership.
   A shared subclass alone does not justify a substitution: compare range, block,
   cost, skill timing and tactical role. Do not silently lower explicit requirements.
5. Observe and verify the intended stage before submitting a local Copilot JSON.
   Record source, modifications and run_id. Warn about squad slot 4 when relevant.
6. Poll the same run; do not duplicate a queued/running job. executor=completed is
   not game_result=full_clear. Use screenshot evidence and actual settlement stars.
7. If still in battle, observe before deciding whether to resume. Cancellation
   is not retreat. A resume requires stopped parent execution and an active battle.
   To abandon a run, use `exit-battle --run-id RUN_ID --expected-stage CODE`.
   Require `exit_verified:true` and `stage.stage_verified:true` before restarting.
   See docs/battle-exit.md for optional arguments, evidence, and limitations.
8. On unknown results, retain evidence and investigate; do not loop blind clicks
   or repeatedly spend sanity. Do not spend premium currency or use unrelated tasks.

Default evidence is .runtime/ in this checkout; MAA_AGENT_RUNTIME_DIR overrides it.
Keep generated rosters, screenshots, logs and local configuration out of commits.

## Plan once, let MAA execute, verify milestones

For routine farming, base management, recruitment, rewards and operator training,
use MAA's task automation as the primary executor. Do not turn a supported MAA
workflow into repeated screenshot/OCR/click cycles.

1. Before execution, establish the current state and write a concrete plan:
   requested outcomes, material deficits, task dependencies, resource limits,
   completion conditions and verification points. Proceed within the user's
   authorization; planning does not require a new approval round.
2. Check the installed frontend's task schema and the Core/resource capabilities
   before queuing work. Core support does not imply maa-cli support. Parse or
   dry-run task configurations where available. If a frontend rejects a task,
   investigate that boundary and use a verified official interface supported by
   the installed Core; do not assume upgrading the stable CLI will fix it.
3. Queue compatible tasks together. Use native continuous auto-deploy (`series`)
   and a bounded run count for farming, accounting for remaining material needs
   and sanity. Recalculate after a batch when drops are random. For training,
   collect missing chip packs before manufacturing dual chips, then promote,
   level and train skills. Distinguish farming, chip conversion and dual-chip
   manufacturing; do not convert materials without checking actual stock.
4. Observe before starting, at dependency boundaries that require a decision,
   on actionable errors, and at final completion. Prefer native callbacks and
   logs while a task runs; poll the same job at an interval suited to its duration.
   Avoid redundant full-screen OCR and manual inputs during healthy automation.
   Manual interaction is a fallback for unsupported steps or specific failures.
5. Translate resource preferences into actual parameters. For expiring-first
   sanity medicine, check the installed Core's expiration-selection semantics;
   a medicine count alone does not guarantee that preference. Keep stone usage
   at zero unless explicitly authorized. Inspect consumption callbacks and
   report any deviation promptly; never claim a preference was honored without
   evidence.
6. When the user takes over or reports a step completed, stop issuing game input,
   stop the automation controlling that step, and observe once after handover.
   Discard stale coordinates, inventory assumptions and queued duplicate work.
   Resume only the remaining authorized steps from the newly observed state.
7. On failure, retain evidence and choose a focused recovery path. Do not repeat
   the same failing approach or expand into unrelated source/install research.
   Explain a blocker promptly and switch to a supported path when available.
8. Verify the requested final values explicitly (for example, elite 2, level 60,
   skill rank 7). Update only verified roster fields and preserve unknowns. Report
   completed work, remaining work and actual resource use separately from
   executor status. Keep account-specific evidence under ignored local paths.

Session lesson (2026-11-03): a training task was rejected by maa-cli even though
the installed MaaCore accepted it through the official Python API. Single-run
farming and excessive manual OCR/navigation then added avoidable latency. Future
runs must validate the execution interface first, batch native tasks, and reserve
Agent interaction for planning, exceptions and milestone verification.

Screen-coordinate Copilot actions: see [docs/copilot-actions.md](docs/copilot-actions.md).
Inspect the normalized game image, camera state and author requirements before
using Click/Swipe scripts; in-bounds coordinates alone do not establish a valid target.
