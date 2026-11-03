"""Configure macOS MuMu ADB without sending game inputs."""
import json
import os
from pathlib import Path
import platform
import subprocess

from .config import cli_directory, executable, profile_name

MUMUTOOL = '/Applications/MuMuPlayer.app/Contents/MacOS/mumutool'


def command(args, env=None):
    result = subprocess.run([str(arg) for arg in args], capture_output=True,
                            text=True, timeout=20, check=True, env=env)
    return result.stdout.strip()


def select_device(info):
    """Never fall back to another device when MuMu reports multiple instances."""
    results = info.get('return', {}).get('results', [])
    if not isinstance(results, list):
        raise ValueError('Unexpected mumutool response; pass --address explicitly')
    running = [item for item in results if item.get('state') == 'running']
    if len(running) > 1:
        raise ValueError('Multiple MuMu instances are running; pass --address explicitly')
    if not running:
        raise ValueError('No running MuMu instance; start MuMu or pass --address explicitly')
    port = running[0].get('adb_port')
    if isinstance(port, bool) or not str(port).isdigit() or not 1 <= int(port) <= 65535:
        raise ValueError('MuMu did not report a valid adb_port; pass --address explicitly')
    return f'127.0.0.1:{int(port)}'


def setup(address=None, mumutool=MUMUTOOL):
    if platform.system() != 'Darwin':
        raise ValueError('setup-macos is only supported on macOS')
    cli = executable(os.environ.get('MAA_AGENT_CLI', 'maa'), 'MAA CLI')
    env = os.environ.copy()
    for name in ('CONFIG', 'DATA'):
        override = env.get(f'MAA_AGENT_{name}_DIR')
        if override:
            env[f'MAA_{name}_DIR'] = str(Path(override).expanduser().resolve())
    config = cli_directory(cli, 'config', env)
    profile = profile_name(os.environ.get('MAA_AGENT_PROFILE', 'default'))
    profiles = config / 'profiles'
    existing = next((profiles / f'{profile}.{ext}' for ext in ('json', 'yaml', 'yml', 'toml')
                     if (profiles / f'{profile}.{ext}').exists()), None)
    if existing:
        if address is not None:
            raise ValueError(f'Profile already exists: {existing}; edit it or select a new '
                             'MAA_AGENT_PROFILE to use --address (nothing overwritten)')
        return {'ok': True, 'created': False, 'profile': str(existing),
                'next': 'doctor', 'message': 'Existing profile preserved'}
    adb = executable('adb', 'ADB')
    if address is None:
        tool = Path(mumutool).expanduser()
        if not tool.is_file():
            raise ValueError('mumutool not found; pass --mumutool PATH or --address explicitly')
        address = select_device(json.loads(command([tool, 'info', 'all'])))
    if not isinstance(address, str) or not address.strip() or any(c.isspace() for c in address):
        raise ValueError('ADB address must be a nonempty address without whitespace')
    if ':' in address:
        command([adb, 'connect', address])
    if command([adb, '-s', address, 'get-state']) != 'device':
        raise ValueError('ADB is not ready; start MuMu and authorize the connection')
    content = {'connection': {'preset': 'ADB', 'adb_path': str(adb),
                              'address': address, 'config': 'CompatMac'},
               'instance_options': {'touch_mode': 'MaaTouch', 'kill_adb_on_exit': False}}
    profiles.mkdir(parents=True, exist_ok=True)
    path = profiles / f'{profile}.json'
    # Exclusive creation also protects a profile created concurrently.
    with path.open('x', encoding='utf-8') as output:
        output.write(json.dumps(content, ensure_ascii=False, indent=2) + '\n')
    return {'ok': True, 'created': True, 'profile': str(path),
            'device': address, 'next': 'doctor'}
