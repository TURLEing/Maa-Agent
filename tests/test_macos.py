import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from maa_agent.macos import select_device, setup


def report(*instances):
    return {'return': {'results': list(instances)}}


class MuMuDiscoveryTests(unittest.TestCase):
    def test_uses_actual_running_instance_port(self):
        self.assertEqual(select_device(report(
            {'state': 'stopped', 'adb_port': 16384},
            {'state': 'running', 'adb_port': '16416'})), '127.0.0.1:16416')

    def test_multiple_instances_require_explicit_selection(self):
        with self.assertRaisesRegex(ValueError, 'Multiple MuMu'):
            select_device(report({'state': 'running', 'adb_port': 16416},
                                 {'state': 'running', 'adb_port': 16448}))

    def test_stopped_instances_are_not_connected(self):
        with self.assertRaisesRegex(ValueError, 'No running'):
            select_device(report({'state': 'stopped', 'adb_port': 16384}))

    def test_invalid_ports_are_not_used(self):
        for port in (None, 0, 65536, True, 'oops'):
            with self.subTest(port=port), self.assertRaisesRegex(ValueError, 'valid adb_port'):
                select_device(report({'state': 'running', 'adb_port': port}))


class MacSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.profile = self.root / 'profiles/default.json'
        self.tool = self.root / 'MuMu App/mumutool'
        self.tool.parent.mkdir()
        self.tool.touch()
        for mock in (patch('maa_agent.macos.platform.system', return_value='Darwin'),
                     patch.dict(os.environ, {}, clear=True),
                     patch('maa_agent.macos.executable', side_effect=lambda value, label: Path(value)),
                     patch('maa_agent.macos.cli_directory', return_value=self.root)):
            mock.start()
            self.addCleanup(mock.stop)

    def test_discovers_connects_and_writes_compatible_profile(self):
        with patch('maa_agent.macos.command', side_effect=[
                json.dumps(report({'state': 'running', 'adb_port': 16416})),
                'connected', 'device']) as command:
            result = setup(mumutool=self.tool)
        content = json.loads(self.profile.read_text())
        self.assertTrue(result['created'])
        self.assertEqual(content['connection']['address'], '127.0.0.1:16416')
        self.assertEqual(content['connection']['config'], 'CompatMac')
        self.assertEqual(content['instance_options']['touch_mode'], 'MaaTouch')
        self.assertFalse(content['instance_options']['kill_adb_on_exit'])
        self.assertEqual(command.call_args_list[-1].args[0],
                         [Path('adb'), '-s', '127.0.0.1:16416', 'get-state'])

    def test_existing_profile_is_preserved_without_adb_calls(self):
        self.profile.parent.mkdir()
        self.profile.write_text('keep unchanged')
        with patch('maa_agent.macos.command') as command:
            self.assertFalse(setup()['created'])
            command.assert_not_called()
        self.assertEqual(self.profile.read_text(), 'keep unchanged')

    def test_explicit_address_cannot_silently_ignore_existing_profile(self):
        self.profile.parent.mkdir()
        self.profile.write_text('keep unchanged')
        with self.assertRaisesRegex(ValueError, 'Profile already exists'):
            setup('127.0.0.1:16448')
        self.assertEqual(self.profile.read_text(), 'keep unchanged')

    def test_offline_device_does_not_create_profile(self):
        with patch('maa_agent.macos.command', side_effect=['connected', 'offline']):
            with self.assertRaisesRegex(ValueError, 'ADB is not ready'):
                setup('127.0.0.1:16416')
        self.assertFalse(self.profile.exists())

    def test_explicit_address_bypasses_mumutool(self):
        with patch('maa_agent.macos.command', side_effect=['connected', 'device']) as command:
            setup('127.0.0.1:16448', mumutool=self.root / 'missing')
        self.assertEqual(command.call_count, 2)

    def test_multiple_instances_do_not_fall_back_or_write_profile(self):
        with patch('maa_agent.macos.command', return_value=json.dumps(report(
                {'state': 'running', 'adb_port': 16416},
                {'state': 'running', 'adb_port': 16448}))) as command:
            with self.assertRaisesRegex(ValueError, 'Multiple MuMu'):
                setup(mumutool=self.tool)
            self.assertEqual(command.call_count, 1)
        self.assertFalse(self.profile.exists())
