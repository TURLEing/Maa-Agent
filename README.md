# Maa-Agent (alpha)

Local tools that let an agent observe and operate Arknights through maa-cli and
MaaFramework. Tested on Windows, MuMu and the Chinese game client.

## Installation

Install Python (tested: 3.13), your emulator/game, ADB, maa-cli and its MAA Core
resources from their official distributions. Log into the game yourself.
Configure maa-cli's `default` JSON profile with `connection.adb_path`,
`connection.device`, and an appropriate touch mode.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m maa_agent observe
```

This alpha supports a source checkout installation. A standalone wheel is not
yet a supported installation workflow. The package does not include MAA models,
templates, game assets, community battle scripts or any player's account data.

See [configuration](docs/configuration.md), [agent instructions](AGENTS.md),
and [roster onboarding](docs/onboarding.md).

## Capabilities

JSON commands: `observe`, `home`, `stage CODE`, `annihilation --expected-stage NAME`,
`run-copilot FILE --expected-stage NAME`, `poll RUN_ID [--observe]`,
`cancel RUN_ID`, `resume --parent RUN_ID --actions FILE`, and `verify`.
Run `python -m maa_agent --help` for arguments.

`run-copilot` changes squad slot 4 and can consume normal sanity. Support units
and sanity potions are disabled. `cancel` stops the executor, not the game battle.
Stage navigation starts from the current chapter map; it does not select arbitrary
chapters. Unknown pages stop with evidence instead of guessing success.

JT8-3 and H8-1 were completed with owned teams and screenshot-verified three-star
results. This is limited real-device validation, not a guarantee for other stages.
Automatic roster-based strategy selection, operator training, full-event planning,
autonomous roguelike play and an MCP server are not implemented.

## Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## License status

This is a local release candidate. The project's source license is pending the
owner's decision. Do not describe this candidate as a licensed public release yet.
See THIRD_PARTY_NOTICES.md for upstream dependencies and resource provenance.
