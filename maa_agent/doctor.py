"""Read-only deployment checks; never sends game input."""
import importlib.metadata
import platform
import subprocess
import sys
from .config import Settings


def diagnose(observe=False):
    checks = []

    def check(name, operation, fix):
        try:
            detail = operation()
            checks.append({'name': name, 'ok': True, 'status': 'passed', 'detail': detail})
            return detail
        except Exception as error:
            checks.append({'name': name, 'ok': False, 'status': 'failed', 'error': str(error), 'fix': fix})

    def command(args, env=None):
        result = subprocess.run([str(arg) for arg in args], capture_output=True,
                                text=True, timeout=20, env=env)
        if result.returncode:
            raise ValueError((result.stderr or result.stdout).strip())
        return result.stdout.strip()

    settings = check('configuration', Settings.load,
                     'Check the installed maa-cli, profile format, configured paths and ADB address; see docs/configuration.md.')
    # Keep the public result JSON serializable, including failures before settings.
    if settings is not None:
        checks[-1]['detail'] = {'cli': str(settings.cli), 'config': str(settings.config),
                                'data': str(settings.data), 'adb': str(settings.adb),
                                'device': settings.device, 'profile': settings.profile}
        check('maa_core', lambda: command([settings.cli, 'version'], settings.cli_environment()),
              'Check that maa-cli can run and that MAA Core is installed in the configured data directory.')

        def resources():
            root = settings.data / 'resource'
            required = ['PaddleOCR/det/inference.onnx', 'PaddleOCR/rec/inference.onnx',
                        'PaddleOCR/rec/keys.txt', 'template/QuickSwitch/Menu.png',
                        'template/QuickSwitch/Home.png',
                        'template/Battle/BattleFlag/BattleOfficiallyBegin.png',
                        'template/Battle/StageDrops/StageDrops-Stars-3.png',
                        'template/Battle/StageDrops/StageDrops-Stars-2.png']
            missing = [path for path in required if not (root / path).is_file()]
            if missing:
                raise ValueError(f'Missing MAA resources in {root}: {", ".join(missing)}; run maa install')
            return str(root)

        check('resources', resources, 'Repair MAA resources with maa install or correct MAA_AGENT_DATA_DIR.')

        def device():
            state = command([settings.adb, '-s', settings.device, 'get-state'])
            if state != 'device':
                raise ValueError(f'Device is {state}; connect and authorize ADB first')
            return state

        check('adb_device', device, 'Start the emulator and check its ADB address and authorization.')

    def framework():
        from maa.library import Library
        return Library.version()

    check('maafw', framework, 'Install the project dependencies in the active Python environment and check the native library architecture.')
    check('pillow', lambda: importlib.metadata.version('Pillow'), 'Install the project dependencies in the active Python environment.')
    ok = all(item['ok'] for item in checks)
    if observe and ok:
        def observation():
            from .vision import Vision
            return Vision(settings).observe()
        check('observation', observation, 'Check the emulator capture and recognition resources, then retry doctor --observe.')
        ok = all(item['ok'] for item in checks)
    elif observe:
        checks.append({'name': 'observation', 'ok': None, 'status': 'skipped',
                       'detail': 'Repair failed environment checks before capturing the game.'})
    result = {'ok': ok, 'system': platform.system(), 'architecture': platform.machine(),
              'python': sys.version.split()[0], 'python_executable': sys.executable,
              'checks': checks}
    if not ok:
        result['error'] = 'Deployment checks failed; inspect checks for details'
    return result
