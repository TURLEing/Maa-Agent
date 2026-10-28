<div align="center">

<img src="./logo.png" alt="Maa-Agent Logo" width="256" />

# Maa-Agent

**让 Agent 看懂战局，用好你的干员。**

基于 maa-cli 与 MaaFramework 的明日方舟 Agent 工具集

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D4)
![Status](https://img.shields.io/badge/Status-Alpha-orange)
[![License](https://img.shields.io/badge/License-AGPL--3.0-blue)](./LICENSE)

**简体中文** | [English](./README.en.md)

[快速开始](#快速开始) · [干员档案](./docs/onboarding.md) · [Agent 指南](./AGENTS.md) · [问题反馈](https://github.com/TURLEing/Maa-Agent/issues)

</div>

## 项目介绍

Maa-Agent 为能够执行本地命令的 Agent 提供观察游戏、维护干员档案、运行作业和核验战果的工具。Agent 负责理解任务、挑选作业和分析异常；maa-cli 负责执行自动化任务；MaaFramework 提供截图、识别与必要的交互。

我们希望逐步实现根据自己的干员调整作业、自主完成活动关卡，以及结合局势思考的肉鸽攻略。目前为 **Alpha**，这些长期目标尚未全部实现。

## 亮点功能

- **观察游戏**：输出截图、OCR 与页面判断，让 Agent 在操作前确认现场。
- **维护干员档案**：通过 MAA 扫描已有干员，结合 PRTS 元数据整理名字、等级、精英阶段和职业分支，保留完整档案与精二列表。
- **在线抄作业**：支持 Agent 在线到作业网站寻找作业，并根据你的干员档案调整配队与作业，再执行战斗。
- **核验战果**：区分执行器结束与游戏通关，结合结算星数、剿灭击杀数等证据判断结果；无法确认时返回未知。
- **接入已有 Agent**：CLI 返回 JSON，[AGENTS.md](./AGENTS.md) 沉淀搜索作业、检查练度与分析替换干员的经验。

## 快速开始

### 1. 准备环境

安装 Python（已测试 3.13）、模拟器与游戏、ADB，以及官方 [maa-cli](https://github.com/MaaAssistantArknights/maa-cli) 和 MAA Core 资源。自行登录游戏，配置 maa-cli 的 `default` JSON profile，确保它能连接模拟器。

当前验证环境为 **Windows + MuMu + 国服**；已测试 maa-cli 0.7.5、MAA Core 6.20.1、MaaFramework 5.14.3。配置字段与路径覆盖方式见 [配置说明](./docs/configuration.md)。

### 2. 安装并观察游戏

```powershell
git clone https://github.com/TURLEing/Maa-Agent.git
cd Maa-Agent
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m maa_agent observe
```

当前支持从源码目录安装和运行，尚未支持独立 wheel 安装流程。仓库不附带 MAA 模型、模板、游戏资源、社区作业或玩家账号数据。

### 3. 首先建立自己的干员档案

**首次配队前，请先完成 [干员档案初始化](./docs/onboarding.md)。** 扫描完整持有列表，而不只是精二干员，才能区分“没有这名干员”和“有，但尚未练成”。技能、专精与模组目前不在扫描范围内，需要另行确认。

初始化暂时由多个命令完成；切换账号后需要重新建立对应档案，当前尚无自动账号绑定。

### 4. 交给你的 Agent

让能够访问本地终端的 Agent 阅读 [AGENTS.md](./AGENTS.md)，然后给它具体任务，例如：

> 先观察当前游戏并检查干员档案，再寻找适合我现有干员的 H8-1 作业。核对关卡、技能与练度要求后执行，并通过结算画面确认是否三星。不要使用源石。

Maa-Agent 本身不内置模型，也不要求模型服务密钥；Agent 由你自己的工具提供。当前接口为 CLI，MCP 服务尚未实现。

## 使用说明

运行 `python -m maa_agent --help` 查看完整参数。

| 命令 | 用途 |
| --- | --- |
| `observe` / `verify` | 观察页面 / 核验结果 |
| `home` / `stage CODE` | 返回主页 / 在当前章节地图寻找关卡 |
| `annihilation --expected-stage NAME` | 进入并核对剿灭关卡 |
| `run-copilot FILE --expected-stage NAME` | 执行本地作业 |
| `poll RUN_ID --observe` | 查询任务并观察游戏 |
| `cancel RUN_ID` | 停止执行器；不会自动撤退 |
| `resume --parent RUN_ID --actions FILE` | 原执行已停止且仍在战斗时续接动作 |

`run-copilot` 会修改第 4 编队，并可能消耗正常理智；当前禁用助战与理智药。关卡导航从当前章节地图开始，不能自动选择任意章节。运行记录默认保存在 `.runtime/`，账号档案、截图、日志及本地配置不应提交到仓库。

## 当前进展

已在实机使用自有干员完成 JT8-3、H8-1，并通过结算截图确认三星。这是有限场景验证，不代表任意关卡均可自动完成。

后续方向包括：一键初始化与账号绑定、基于档案的作业匹配、干员替换评估、养成任务、活动规划、肉鸽决策，以及 MCP 接口。

## 参与开发

欢迎通过 [Issues](https://github.com/TURLEing/Maa-Agent/issues) 反馈问题或提交 Pull Request。复现信息请注明工具版本、游戏页面与相关命令，并移除账号及个人信息。

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

简体中文为主要文档语言，英文入口为 [README.en.md](./README.en.md)。修改功能说明时请同步两份 README。

## 致谢与许可

感谢 [MAA](https://github.com/MaaAssistantArknights/MaaAssistantArknights)、[maa-cli](https://github.com/MaaAssistantArknights/maa-cli)、[MaaFramework](https://github.com/MaaXYZ/MaaFramework)、[PRTS Wiki](https://prts.wiki/) 与 [PRTS 作业站](https://prts.plus/) 及其贡献者。首页布局参考 MAA。Maa-Agent 是独立社区项目。

项目代码采用 [GNU AGPL v3.0（AGPL-3.0-only）](./LICENSE)。第三方依赖、数据、作业及游戏相关素材的权利仍归各自权利人，详见 [第三方说明](./THIRD_PARTY_NOTICES.md)。
