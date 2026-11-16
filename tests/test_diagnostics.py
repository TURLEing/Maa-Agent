import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import nullcontext, redirect_stdout
from unittest.mock import Mock, patch

from maa_agent import cli, doctor, runner


class DiagnosticsTests(unittest.TestCase):
    def test_doctor_observe_uses_read_only_observer(self):
        observation = {'state': 'in_battle', 'screenshot': 'capture.png'}
        settings = doctor.Settings(Path('maa'), Path('data'), Path('adb'), 'test-device')
        with patch.object(doctor.Settings, 'load', return_value=settings), \
             patch.object(Path, 'is_file', return_value=True), \
             patch.object(doctor.subprocess, 'run') as run, \
             patch.dict('sys.modules', {'maa.library': Mock(Library=Mock(version=Mock(return_value='5.14.3')))}), \
             patch.object(doctor.importlib.metadata, 'version', return_value='11.0'), \
             patch('maa_agent.vision.Vision') as vision:
            run.return_value.returncode = 0
            run.return_value.stdout = 'device'
            vision.return_value.observe.return_value = observation
            result = doctor.diagnose(observe=True)
        self.assertTrue(result['ok'])
        self.assertEqual(result['checks'][-1]['detail'], observation)
        vision.return_value.observe.assert_called_once_with()
        vision.return_value.home.assert_not_called()

    def test_doctor_cli_continues_checks_after_configuration_failure(self):
        output = io.StringIO()
        with patch.object(doctor.Settings, 'load', side_effect=ValueError('missing profile')), \
             patch.dict('sys.modules', {'maa.library': Mock(Library=Mock(version=Mock(return_value='5.14.3')))}), \
             patch.object(doctor.importlib.metadata, 'version', side_effect=ValueError('missing Pillow')), \
             patch('sys.argv', ['maa-agent', 'doctor', '--observe']), \
             patch('maa_agent.vision.Vision') as vision, redirect_stdout(output):
            with self.assertRaises(SystemExit) as stopped:
                cli.main()
        self.assertEqual(stopped.exception.code, 1)
        result = json.loads(output.getvalue())
        failed = {item['name'] for item in result['checks'] if item['status'] == 'failed'}
        self.assertEqual(failed, {'configuration', 'pillow'})
        self.assertTrue(all(item.get('fix') for item in result['checks'] if item['status'] == 'failed'))
        self.assertEqual(result['checks'][-1]['status'], 'skipped')
        vision.assert_not_called()

    def test_poll_old_run_recovers_context_without_rewriting_result(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            stored = {'run_id': 'abc', 'executor': 'cancelled', 'game_result': 'unknown'}
            (folder / 'result.json').write_text(json.dumps(stored), encoding='utf-8')
            context = {'parent': 'def', 'expected_stage': 'JT8-3'}
            (folder / 'request.json').write_text(json.dumps({'context': context}), encoding='utf-8')
            (folder / 'cli.log').write_text('\n'.join(str(i) for i in range(20)), encoding='utf-8')
            with patch.object(runner, 'run_folder', return_value=folder):
                result = runner.poll('abc')
            self.assertEqual(result['handoff']['context'], context)
            self.assertEqual(result['handoff']['next'], 'observe_or_verify')
            self.assertEqual(result['recent_events'], [str(i) for i in range(8, 20)])
            self.assertEqual(json.loads((folder / 'result.json').read_text()), stored)
            (folder / 'request.json').write_text('broken', encoding='utf-8')
            with patch.object(runner, 'run_folder', return_value=folder):
                self.assertTrue(runner.poll('abc')['handoff']['warnings'])

    def test_worker_retains_last_observation_when_later_capture_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            request = {'context': {'kind': 'copilot', 'expected_stage': 'JT8-3'}, 'task': {}, 'timeout': 30}
            (folder / 'request.json').write_text(json.dumps(request), encoding='utf-8')
            before = {'state': 'stage_ready', 'stage_text': ['JT8-3']}
            transition = {'state': 'unknown', 'screenshot': 'transition.png', 'observed_at': 'saved-time'}
            with patch.object(runner, 'run_folder', return_value=folder), \
                 patch.object(runner.Settings, 'load'), \
                 patch.object(runner, 'device_lock', return_value=nullcontext()), \
                 patch('maa_agent.vision.Vision') as vision, \
                 patch.object(runner, 'execute', return_value={'executor': 'completed'}), \
                 patch.object(runner.time, 'sleep'):
                vision.return_value.observe.side_effect = [before, transition, RuntimeError('disconnected')]
                runner.worker('abc')
                result = runner.poll('abc')
            self.assertEqual(result['executor'], 'error')
            self.assertEqual(result['game_result'], 'unknown')
            self.assertEqual(result['after'], transition)
            self.assertEqual(result['handoff']['last_observation']['phase'], 'after')
            self.assertEqual(result['handoff']['evidence']['screenshot'], 'transition.png')
