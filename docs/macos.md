# macOS 部署（Apple Silicon + MuMu）

使用原生 ARM64 Python 3.11+（推荐 3.12）、maa-cli 0.7.5、MaaFramework
5.14.3，以及 MuMu 中的安卓明日方舟。系统自带的 `/usr/bin/python3`
可能只有 3.9，不能用于本项目。当前观察器使用 ADB，尚不支持 PlayCover。

本机验证环境：macOS 26.6 / arm64、Python 3.12.14、maa-cli 0.7.5、
MAA Core 6.21.1、MaaFramework 5.14.3。已验证 ADB 连接、1280×720 截图、
中文 OCR、游戏首页识别、原生 MAA 干员/仓库扫描、基建、公招、商店、领奖和
芯片关代理作战。尚未验证本框架的 Copilot 自动配队与完整战斗流程。

## 安装

如果缺少依赖，可按官方 [maa-cli 安装说明](https://docs.maa.plus/zh-cn/manual/cli/install.html)
通过 Homebrew 安装；已经安装的依赖无需重复安装：

```bash
brew install MaaAssistantArknights/tap/maa-cli uv
brew install --cask android-platform-tools
```

在 MuMu 中启用 ADB 并启动安卓实例，然后在本仓库根目录运行：

```bash
bash scripts/setup_macos.sh
```

脚本创建 `.venv`，安装项目依赖，在缺失时安装稳定版 MAA Core 及资源，
读取正在运行的 MuMu 实例的真实 ADB 端口，创建 maa-cli 的 `default.json`
并运行检查。不会覆盖同名的现有配置。多个实例运行时必须指定目标地址：

```bash
/Applications/MuMuPlayer.app/Contents/MacOS/mumutool info all
bash scripts/setup_macos.sh 127.0.0.1:PORT
```

`PORT` 替换成 `adb_port`，不能假定固定为 16384。
已有配置需要改地址时，手动编辑 `$(maa dir config)/profiles/default.json`。
显式传入地址而同名配置已存在时会报错，避免静默忽略地址。
需要独立配置时，可先设置 `export MAA_AGENT_PROFILE=maa-agent`，后续命令沿用它。
脚本要求 `maa`、`adb` 已安装；可通过 `MAA_AGENT_CLI` 指定 maa 可执行文件。

已有 Python 环境时，也可以直接调用输出 JSON 的配置命令：

```bash
.venv/bin/python -m maa_agent setup-macos
.venv/bin/python -m maa_agent setup-macos --address 127.0.0.1:PORT
```

MuMu 安装在其他位置时使用 `--mumutool /path/to/mumutool`。自动发现只接受唯一
运行中的 MuMu 实例；发现失败不会猜测端口或选取其他 ADB 设备。配置命令不
安装依赖、不启动模拟器、不登录游戏，也不发送游戏输入；已有配置原样保留。

## 检查和使用

```bash
.venv/bin/python -m maa_agent doctor
.venv/bin/python -m maa_agent observe
```

`doctor` 检查配置、引擎、资源、ADB 与依赖，不发送游戏输入；`observe` 截图并运行 OCR。
自行在模拟器内登录目标账号，并停在游戏首页，然后再次运行 `observe`。
正常情况下首页返回 `state: "home"`，截图和识别证据保存在 `.runtime/observations/`。
登录页目前可能返回 `unknown`，不表示部署失败。

也可使用 `.venv/bin/maa-agent doctor`。无需修改全局 Python 或设置模型服务密钥。
用 `source .venv/bin/activate` 激活环境后，可以省略 `.venv/bin/`。

配置由 `maa dir config`、`maa dir data` 自动发现。macOS 默认位于
`~/Library/Application Support/com.loong.maa/`，不是 Windows 的 AppData 目录。
手动配置示例见 [profile.macos.json](../examples/profile.macos.json)，覆盖变量见
[配置说明](configuration.md)。

## 首次干员扫描

登录并确认账号后，清除干员筛选条件，按 [初始化说明](onboarding.md) 建立完整档案。
macOS 命令如下；扫描会操作游戏界面，请在需要建立档案时运行：

```bash
mkdir -p debug
maa run "$PWD/tasks/scan-operators.json" --batch -vv --log-file=./debug/operators-new.log
.venv/bin/python scripts/operator_roster.py refresh-catalog
.venv/bin/python scripts/operator_roster.py import-scan debug/operators-new.log
.venv/bin/python scripts/operator_roster.py query OPERATOR_NAME
```

任务文件必须使用绝对路径；maa-cli 会把相对路径解释为其配置目录下的任务文件。
若使用非默认 profile，给 `maa run` 加 `-p PROFILE`。直接运行 `maa` 时，
用原生 `MAA_CONFIG_DIR` / `MAA_DATA_DIR` 选择自定义目录；`MAA_AGENT_*` 只供项目读取。
扫描不包含技能、专精或模组。切换账号后重新建立对应档案。

## 常见问题

- ADB 离线：确认 MuMu 正在运行，通过 `mumutool info all` 核对端口，再执行
  `adb connect 127.0.0.1:PORT` 与 `adb -s 127.0.0.1:PORT get-state`。
- 多条 ADB 地址可能指向同一台模拟器。配置使用 MuMu 返回的端口，避免自动选择错误实例。
- 连接配置使用 `CompatMac`，触控使用 `MaaTouch`，不使用 PlayCover 的 `MacPlayTools`。
- `doctor` 提示缺少 Core 或 OCR 模型：执行 `maa install stable --batch`；已有安装则用
  `maa update`。首次下载较大，需保持网络可用。
- 截图必须能归一化到 1280×720；建议模拟器保持 16:9 横屏。项目会拒绝不匹配的截图尺寸。
- 原生库加载失败：用 `uname -m` 和 `.venv/bin/python -c 'import platform; print(platform.machine())'`
  确认架构一致，避免混用 Rosetta Python 和 ARM64 库。
- `doctor` 中只有 `adb_device` 失败：部署依赖可能正常，目标实例未运行或尚未连接。
  先核对当前端口，再连接；不要因此重复安装 Python 或 MAA。
- `unknown variant OperProgress`：这是执行前端的任务类型限制，不能据此判断
  MaaCore 缺少训练能力。先核对所用 CLI 的任务 schema；本框架尚未提供正式的
  Core API 后端，也没有开放干员养成命令。不要用一次临时 API 成功执行来宣称
  框架已支持完整养成，也不要假定只更新 Core 或稳定版 CLI 就能解决。

## 开发验证

```bash
.venv/bin/python -m unittest discover -s tests -v
```

GitHub Actions 在 macOS 与 Windows 上运行单元测试；测试覆盖实例选择、配置
保留、失败时不写配置、带空格的目录、子进程环境传递和 POSIX 设备锁。
CI 不包含模拟器或真实游戏，不能代替实机验证。

自动战斗仍遵循 [AGENTS.md](../AGENTS.md) 的关卡核验、干员检查和战果确认要求。
部署、观察和原生代理验证不代表已验证框架的 Copilot 自动战斗。
