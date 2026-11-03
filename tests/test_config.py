import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from maa_agent.config import Settings
from maa_agent import runner


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = self.root / 'Application Support/maa/config'
        self.data = self.root / 'Application Support/maa'
        self.profiles = self.config / 'profiles'
        self.profiles.mkdir(parents=True)
        # Tests discover files without launching either executable.
        self.cli = self.root / 'maa'
        self.adb = self.root / 'adb'
        self.cli.touch()
        self.adb.touch()
        self.environment = patch.dict(os.environ, {'MAA_AGENT_CLI': str(self.cli)}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.process = patch('maa_agent.config.subprocess.run', side_effect=self.directory)
        self.process.start()
        self.addCleanup(self.process.stop)

    def directory(self, args, **kwargs):
        directories = {'config': self.config, 'data': self.data}
        return subprocess.CompletedProcess(args, 0, str(directories[args[-1]]) + '\n', '')

    def profile(self, connection=None, **extra):
        content = {'connection': connection if connection is not None else {
            'adb_path': str(self.adb), 'address': '127.0.0.1:16416'}, **extra}
        (self.profiles / 'default.json').write_text(json.dumps(content), encoding='utf-8')

    def test_discovers_mac_directories_with_spaces(self):
        self.profile()
        settings = Settings.load()
        self.assertEqual(settings.config, self.config)
        self.assertEqual(settings.data, self.data)
        self.assertEqual(settings.device, '127.0.0.1:16416')

    def test_legacy_windows_device_field_is_supported(self):
        self.profile({'adb_path': str(self.adb), 'device': 'emulator-5554'})
        self.assertEqual(Settings.load().device, 'emulator-5554')

    def test_toml_profile_and_adb_on_path(self):
        (self.profiles / 'default.toml').write_text('[connection]\naddress="emulator-5554"\n', encoding='utf-8')
        with patch('maa_agent.config.shutil.which', side_effect=lambda value: str(self.adb) if value == 'adb' else None):
            self.assertEqual(Settings.load().adb, self.adb)

    def test_json_precedes_toml_like_maa_cli(self):
        self.profile()
        (self.profiles / 'default.toml').write_text('[connection]\naddress="wrong-device"\n', encoding='utf-8')
        self.assertEqual(Settings.load().device, '127.0.0.1:16416')

    def test_yaml_does_not_silently_fall_back_to_different_toml(self):
        (self.profiles / 'default.yaml').touch()
        (self.profiles / 'default.toml').touch()
        with self.assertRaisesRegex(ValueError, 'YAML profiles'):
            Settings.load()

    def test_agent_overrides_reach_the_executor(self):
        self.profile()
        with patch.dict(os.environ, {'MAA_AGENT_CONFIG_DIR': str(self.config),
                                     'MAA_AGENT_DATA_DIR': str(self.data), 'UNRELATED': 'kept'}):
            settings = Settings.load()
            self.assertEqual(settings.cli_environment()['MAA_CONFIG_DIR'], str(self.config))
            self.assertEqual(settings.cli_environment()['MAA_DATA_DIR'], str(self.data))
            self.assertEqual(settings.cli_environment()['UNRELATED'], 'kept')

    def test_native_maa_overrides_are_honored(self):
        self.profile()
        with patch.dict(os.environ, {'MAA_CONFIG_DIR': str(self.config), 'MAA_DATA_DIR': str(self.data)}):
            self.assertEqual(Settings.load().config, self.config)
            self.assertEqual(Settings.load().data, self.data)

    def test_missing_profile_has_actionable_error(self):
        with self.assertRaisesRegex(ValueError, 'MAA profile not found'):
            Settings.load()

    def test_missing_cli_is_reported_before_configuration(self):
        with patch.dict(os.environ, {'MAA_AGENT_CLI': str(self.root / 'missing')}):
            with self.assertRaisesRegex(ValueError, 'MAA CLI not found'):
                Settings.load()

    def test_missing_adb_is_rejected(self):
        self.profile({'adb_path': str(self.root / 'missing'), 'address': 'emulator-5554'})
        with self.assertRaisesRegex(ValueError, 'ADB not found'):
            Settings.load()

    def test_ambiguous_device_is_not_automatically_selected(self):
        self.profile({'adb_path': str(self.adb)})
        with self.assertRaisesRegex(ValueError, 'connection.address explicitly'):
            Settings.load()

    def test_playcover_is_rejected_before_adb_connection(self):
        self.profile({'preset': 'PlayCover', 'address': '127.0.0.1:1717'})
        with self.assertRaisesRegex(ValueError, 'PlayCover is not supported'):
            Settings.load()

    def test_unknown_profile_version_is_rejected(self):
        self.profile(version=2)
        with self.assertRaisesRegex(ValueError, 'Unsupported profile version'):
            Settings.load()

    def test_profile_cannot_escape_directory(self):
        for profile in ('../other', '..\\other', '.', '..', ''):
            with self.subTest(profile=profile), patch.dict(os.environ, {'MAA_AGENT_PROFILE': profile}):
                with self.assertRaisesRegex(ValueError, 'profile name'):
                    Settings.load()


@unittest.skipIf(os.name == 'nt', 'POSIX process and flock checks')
class PosixDeploymentTests(unittest.TestCase):
    def test_real_executor_receives_config_and_data_paths_with_spaces(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            cli = root / 'fake maa'
            cli.write_text('#!/bin/sh\nprintf "%s\\n%s\\n" "$MAA_CONFIG_DIR" "$MAA_DATA_DIR"\n', encoding='utf-8')
            cli.chmod(0o755)
            settings = Settings(cli, root / 'data folder', root / 'adb', 'emulator-5554',
                                config=root / 'config folder')
            folder = root / 'run folder'
            result = runner.execute(settings, {'tasks': []}, folder, timeout=5)
            self.assertEqual(result['executor'], 'completed')
            self.assertEqual((folder / 'cli.log').read_text().splitlines(),
                             [str(settings.config), str(settings.data)])

    def test_lock_creates_nested_runtime_and_reports_contention(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / 'nested/runtime'
            with patch.object(runner, 'RUNTIME', runtime):
                with runner.device_lock():
                    with self.assertRaisesRegex(ValueError, 'device_busy'):
                        with runner.device_lock():
                            self.fail('Second operation acquired a busy lock')
                with runner.device_lock():
                    self.assertTrue((runtime / 'device.lock').is_file())
