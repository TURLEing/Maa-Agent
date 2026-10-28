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
8. On unknown results, retain evidence and investigate; do not loop blind clicks
   or repeatedly spend sanity. Do not spend premium currency or use unrelated tasks.

Default evidence is .runtime/ in this checkout; MAA_AGENT_RUNTIME_DIR overrides it.
Keep generated rosters, screenshots, logs and local configuration out of commits.
