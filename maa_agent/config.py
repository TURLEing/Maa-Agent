from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get('MAA_AGENT_RUNTIME_DIR', ROOT / '.runtime')).expanduser().resolve()


def executable(value, label):
    expanded = os.path.expanduser(str(value))
    path = Path(shutil.which(expanded) or expanded)
    if not path.is_file():
        raise ValueError(f'{label} not found: {value}')
    return path.resolve()


def cli_directory(cli, name, env):
    try:
        output = subprocess.run([str(cli), 'dir', name], env=env, check=True,
                                capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError(f'Cannot discover maa-cli {name} directory: {error}') from error
    path = output.stdout.strip()
    if not path:
        raise ValueError(f'maa dir {name} returned an empty path')
    return Path(path).expanduser().resolve()


def profile_name(value):
    if not value or Path(value).name != value or '/' in value or '\\' in value or value in ('.', '..'):
        raise ValueError('MAA_AGENT_PROFILE must be a profile name, not a path')
    return value


@dataclass(frozen=True)
class Settings:
    cli: Path
    data: Path
    adb: Path
    device: str
    profile: str = 'default'
    config: Path | None = None

    def cli_environment(self):
        env = os.environ.copy()
        if self.config is not None:
            env['MAA_CONFIG_DIR'] = str(self.config)
        env['MAA_DATA_DIR'] = str(self.data)
        return env

    @classmethod
    def load(cls):
        cli_path = os.environ.get('MAA_AGENT_CLI') or shutil.which('maa')
        if not cli_path and os.name == 'nt':
            cli_path = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'Programs/maa-cli/maa.exe'
        if not cli_path:
            raise ValueError('MAA CLI not found; install maa-cli or set MAA_AGENT_CLI')
        cli = executable(cli_path, 'MAA CLI')
        env = os.environ.copy()
        if os.environ.get('MAA_AGENT_CONFIG_DIR'):
            env['MAA_CONFIG_DIR'] = str(Path(os.environ['MAA_AGENT_CONFIG_DIR']).expanduser().resolve())
        if os.environ.get('MAA_AGENT_DATA_DIR'):
            env['MAA_DATA_DIR'] = str(Path(os.environ['MAA_AGENT_DATA_DIR']).expanduser().resolve())
        config = (Path(env['MAA_CONFIG_DIR']).expanduser().resolve() if env.get('MAA_CONFIG_DIR')
                  else cli_directory(cli, 'config', env))
        data = (Path(env['MAA_DATA_DIR']).expanduser().resolve() if env.get('MAA_DATA_DIR')
                else cli_directory(cli, 'data', env))
        profile = profile_name(os.environ.get('MAA_AGENT_PROFILE', 'default'))
        # Match maa-cli's format precedence; YAML needs an explicit conversion.
        candidates = [config / 'profiles' / f'{profile}.{ext}' for ext in ('json', 'yaml', 'yml', 'toml')]
        source = next((path for path in candidates if path.is_file()), None)
        if source is None:
            raise ValueError(f'MAA profile not found: {config / "profiles" / profile}; create a JSON or TOML profile')
        if source.suffix in ('.yaml', '.yml'):
            raise ValueError(f'YAML profiles are not supported by Maa-Agent; convert {source} to JSON or TOML')
        text = source.read_text(encoding='utf-8')
        content = json.loads(text) if source.suffix == '.json' else tomllib.loads(text)
        if content.get('version', 1) != 1:
            raise ValueError('Unsupported profile version; use a maa-cli 0.7.x profile')
        connection = content.get('connection', {})
        preset = connection.get('preset', 'ADB').lower()
        if preset not in ('adb', 'mumupro'):
            raise ValueError('Maa-Agent observation requires an ADB/MuMuPro profile; PlayCover is not supported')
        adb_default = '/Applications/MuMuPlayer.app/Contents/MacOS/MuMuEmulator.app/Contents/MacOS/tools/adb' if preset == 'mumupro' else 'adb'
        adb = executable(connection.get('adb_path', adb_default), 'ADB')
        device = connection.get('address') or connection.get('device')
        if not isinstance(device, str) or not device.strip():
            raise ValueError(f'Set connection.address explicitly in {source}; use adb devices to find it')
        return cls(cli, data, adb, device.strip(), profile, config)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)
