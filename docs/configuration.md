# Configuration

The adapter reads a maa-cli 0.7.x JSON or TOML profile. It discovers platform
directories using `maa dir config` and `maa dir data`, including macOS paths
containing spaces. `MAA_CONFIG_DIR`, `MAA_DATA_DIR`, and XDG overrides are honored.
Set the device address explicitly. YAML profiles must be converted to JSON or TOML.
When several formats share a name, maa-cli's precedence is JSON, YAML, YML, TOML;
Maa-Agent reports unsupported YAML instead of reading a different profile.

| Environment variable | Meaning |
| --- | --- |
| MAA_AGENT_CLI | Full path to maa / maa.exe; otherwise PATH (plus legacy Windows installation discovery) |
| MAA_AGENT_CONFIG_DIR | Directory containing profiles/PROFILE.json or .toml |
| MAA_AGENT_PROFILE | Profile name; default is default |
| MAA_AGENT_DATA_DIR | MAA data directory containing resource/ |
| MAA_AGENT_RUNTIME_DIR | Writable evidence/job directory; default checkout/.runtime |

Agent config/data overrides take priority over native maa-cli variables and are
passed to child maa-cli processes as `MAA_CONFIG_DIR` / `MAA_DATA_DIR`, so observation
and execution use the same installation. Paths support `~` expansion.

See examples/profile.json or examples/profile.macos.json. Replace placeholders.
`connection.address` is the preferred device key; legacy `connection.device` is
also accepted. `adb_path` can be an absolute path or a command on PATH (default:
`adb`; the MuMuPro preset uses MuMu's bundled ADB). ADB and MuMuPro presets are
supported; PlayCover cannot be observed by the current AdbController.

Run `python -m maa_agent doctor` to check configuration, MaaCore, OCR/templates,
ADB connectivity and native Python dependencies without sending game input.
See [macOS deployment](macos.md) for setup and troubleshooting.

Original Windows validation: maa-cli 0.7.5, MAA Core 6.20.1, MaaFramework 5.14.3.
The observer uses the installed Core PaddleOCR models and recognition templates.
Missing resources require repairing the official MAA installation.
