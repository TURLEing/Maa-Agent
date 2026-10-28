from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get('MAA_AGENT_RUNTIME_DIR', ROOT / '.runtime')).resolve()


@dataclass(frozen=True)
class Settings:
    cli: Path
    data: Path
    adb: Path
    device: str
    profile: str = 'default'

    @classmethod
    def load(cls):
        config = Path(os.environ.get('MAA_AGENT_CONFIG_DIR', Path(os.environ.get('APPDATA', Path.home() / 'AppData/Roaming')) / 'loong/maa/config'))
        profile = os.environ.get('MAA_AGENT_PROFILE', 'default')
        connection = json.loads((config / 'profiles' / f'{profile}.json').read_text(encoding='utf-8'))['connection']
        cli = Path(os.environ.get('MAA_AGENT_CLI') or shutil.which('maa') or Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'Programs/maa-cli/maa.exe')
        if not cli.is_file():
            raise ValueError('MAA CLI not found; set MAA_AGENT_CLI')
        return cls(cli, Path(os.environ.get('MAA_AGENT_DATA_DIR', config.parent / 'data')),
                   Path(connection['adb_path']), connection['device'], profile)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)
