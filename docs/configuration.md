# Configuration

The current adapter reads a maa-cli JSON profile. TOML profiles and automatic
device discovery are not supported yet. Use maa-cli to verify connectivity first.

| Environment variable | Meaning |
| --- | --- |
| MAA_AGENT_CLI | Full path to maa.exe; otherwise PATH/local installation discovery |
| MAA_AGENT_CONFIG_DIR | Directory containing profiles/default.json |
| MAA_AGENT_PROFILE | Profile name; default is default |
| MAA_AGENT_DATA_DIR | MAA data directory containing resource/ |
| MAA_AGENT_RUNTIME_DIR | Writable evidence/job directory; default checkout/.runtime |

The profile must also be discoverable by maa-cli itself; the config-dir override
here selects what this adapter reads, not maa-cli's own config-root setting.
See examples/profile.json. Replace its placeholders before using it.

Tested versions: maa-cli 0.7.5, MAA Core 6.20.1, MaaFramework 5.14.3.
The observer uses the installed Core PaddleOCR models and recognition templates.
Missing resources require repairing the official MAA installation.
