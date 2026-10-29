<div align="center">

<img src="./logo.png" alt="Maa-Agent Logo" width="256" />

# Maa-Agent

**Help your agent understand the battle and work with your roster.**

An Arknights agent toolkit built on maa-cli and MaaFramework

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D4)
![Status](https://img.shields.io/badge/Status-Alpha-orange)
[![License](https://img.shields.io/badge/License-AGPL--3.0-blue)](./LICENSE)

[简体中文](./README.md) | **English**

[Quick start](#quick-start) · [Roster setup](./docs/onboarding.md) · [Agent guide](./AGENTS.md) · [Issues](https://github.com/TURLEing/Maa-Agent/issues)

</div>

## About

Maa-Agent gives agents with local command access tools to observe Arknights, maintain operator records, run battle scripts, and verify outcomes. The agent interprets tasks, selects strategies, and investigates problems; maa-cli executes automation; MaaFramework provides screenshots, recognition, and additional interaction.

Our ultimate vision is to adapt strategies to your own roster, complete event stages autonomously, clear Integrated Strategies through situational decisions, and reach the summit of Contingency Contract! This project is currently in **Alpha**; those goals are not all implemented.

## Features

- **Game observation**: screenshots, OCR, and page classification help agents inspect the game before acting.
- **Operator records**: scan owned operators through MAA and combine PRTS metadata with names, levels, elite phases, classes, and subclasses. Retain both the full roster and an Elite 2 list.
- **Community strategies**: let your agent find strategies on community websites, adapt their teams and battle plans to your operator roster, and execute them in-game.
- **Outcome verification**: distinguish executor completion from a game clear using evidence such as settlement stars and annihilation kill counts. Uncertain outcomes remain unknown.
- **Agent integration**: JSON CLI output and [AGENTS.md](./AGENTS.md) document strategy search, requirement checks, and operator substitution reasoning.

## Quick start

### 1. Prepare your environment

Install Python (tested with 3.13), an emulator and the game, ADB, and official [maa-cli](https://github.com/MaaAssistantArknights/maa-cli) with MAA Core resources. Log into the game yourself. Configure maa-cli's `default` JSON profile and verify emulator connectivity.

Validated on **Windows + MuMu + the Chinese game client**, with maa-cli 0.7.5, MAA Core 6.20.1, and MaaFramework 5.14.3. See [configuration](./docs/configuration.md) for profile fields and path overrides.

### 2. Install and observe

```powershell
git clone https://github.com/TURLEing/Maa-Agent.git
cd Maa-Agent
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m maa_agent observe
```

This alpha supports installation and execution from a source checkout. Standalone wheel installation is not yet supported. MAA models, templates, game assets, community battle scripts, and player account data are not bundled.

### 3. Initialize your roster first

**Complete [roster setup](./docs/onboarding.md) before selecting your first team.** Scan all owned operators, not just Elite 2 operators, to distinguish an unowned operator from one that has not been raised yet. Skills, masteries, and modules are not scanned and need separate verification.

Setup currently takes multiple commands. Rebuild the appropriate roster after switching accounts; automatic account binding is not implemented.

### 4. Connect your agent

Ask an agent with local terminal access to read [AGENTS.md](./AGENTS.md), then give it a concrete task, for example:

> Observe the game and check my roster first. Find an H8-1 strategy suitable for my owned operators, verify its stage and skill/level requirements, then execute it and confirm a three-star clear from the settlement screen. Do not spend Originite Prime.

Maa-Agent does not include a model or require model-provider credentials. Bring your own agent. Have your agent read this README and the [agent guide](./AGENTS.md), and it will know how to get started!

## Usage

Run `python -m maa_agent --help` for full arguments.

| Command | Purpose |
| --- | --- |
| `observe` / `verify` | Observe the page / verify the outcome |
| `home` / `stage CODE` | Return home / find a stage on the current chapter map |
| `annihilation --expected-stage NAME` | Open and check an annihilation stage |
| `run-copilot FILE --expected-stage NAME` | Execute a local battle script |
| `poll RUN_ID --observe` | Poll a run and observe the game |
| `cancel RUN_ID` | Stop the executor; does not retreat from battle |
| `exit-battle --run-id RUN_ID --expected-stage CODE` | Stop execution, exit combat, and verify the returned stage page; [details (Chinese)](./docs/battle-exit.md) |
| `resume --parent RUN_ID --actions FILE` | Resume actions when the parent executor has stopped and battle is still active |

`run-copilot` modifies squad slot 4 and may consume normal sanity. Support units and sanity potions are disabled. Stage navigation starts from the current chapter map; arbitrary chapter selection is not supported. Run evidence defaults to `.runtime/`. Keep account records, screenshots, logs, and local configuration out of commits.

## Progress

- [x] Game screenshots, OCR, and page recognition
- [x] Operator scanning, roster records, and an Elite 2 list
- [x] Agent-led online strategy search and roster-based team and strategy adjustments
- [x] Strategy execution, polling, cancellation, and conditional battle resumption
- [x] Continuous battle exit and verification of the returned stage page
- [x] Outcome verification using settlement screens
- [ ] One-command roster setup and account binding
- [ ] Automated strategy matching and operator substitution evaluation tools
- [ ] Operator training tasks
- [ ] Event stage planning and consecutive clears
- [ ] Situational analysis and autonomous decisions in Integrated Strategies
- [ ] Contingency Contract

## Contributing

Report issues through [GitHub Issues](https://github.com/TURLEing/Maa-Agent/issues) or submit a pull request. Include tool versions, game state, and relevant commands; remove account and personal information from evidence.

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Simplified Chinese is the primary documentation language. The English version is available in [README.en.md](./README.en.md).

## Acknowledgments and license

Thanks to [MAA](https://github.com/MaaAssistantArknights/MaaAssistantArknights), [maa-cli](https://github.com/MaaAssistantArknights/maa-cli), [MaaFramework](https://github.com/MaaXYZ/MaaFramework), [PRTS Wiki](https://prts.wiki/), [PRTS Copilot](https://prts.plus/), and their contributors. Maa-Agent is an independent community project licensed under [GNU AGPL v3.0 (AGPL-3.0-only)](./LICENSE). Third-party dependencies, data, battle scripts, and game-related artwork remain subject to their respective rights and terms. See [third-party notices](./THIRD_PARTY_NOTICES.md).
