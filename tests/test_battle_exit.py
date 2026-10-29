import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from maa_agent.battle_exit import exit_action, exit_battle
from maa_agent import runner


def word(text, x=500, y=300, score=.99):
    return {'text': text, 'score': score, 'box': [x, y, 100, 25]}


def observation(state='unknown', words=()):
    return {'state': state, 'words': list(words), 'screenshot': 'evidence.png'}


class ExitTests(unittest.TestCase):
    def test_pause_needs_battle_counter(self):
        self.assertEqual(exit_action(observation(words=[word('PAUSE')]))[0], 'unknown')
        self.assertEqual(exit_action(observation(words=[word('PAUSE'), word('38/51', 540, 20)]))[0], 'open_quit')
        self.assertEqual(exit_action(observation(words=[word('暂停中'), word('38/5|', 540, 20)]))[0], 'open_quit')

    def test_confirmation_requires_dialog_and_button_region(self):
        prompt = [word('是否放弃行动？'), word('全部返还')]
        self.assertEqual(exit_action(observation(words=prompt + [word('放弃行动', 200, 550)]))[0], 'unknown')
        self.assertEqual(exit_action(observation(words=prompt + [word('放弃行动', 900, 560)]))[0], 'confirm_quit')
        self.assertEqual(exit_action(observation(words=[word('放弃行动', 900, 560)]))[0], 'unknown')

    def test_full_exit_with_loading_and_duplicate_frame(self):
        battle = observation('in_battle')
        confirm = observation(words=[word('是否放弃行动？'), word('全部返还'), word('放弃行动', 900, 560)])
        vision = Mock()
        vision.controller.post_click.return_value = Mock(done=True, succeeded=True)
        vision.observe.side_effect = [battle, battle, confirm, observation(), observation('failure'),
                                     observation('settlement'), observation('navigable_page', [word('H8-4')])]
        with patch('maa_agent.battle_exit.time.sleep'):
            result = exit_battle(vision)
        self.assertTrue(result['exit_verified'])
        self.assertEqual(vision.controller.post_click.call_count, 4)

    def test_unknown_page_does_not_click_or_claim_stopped(self):
        vision = Mock()
        vision.observe.return_value = observation()
        result = exit_battle(vision)
        self.assertFalse(result['exit_verified'])
        self.assertIsNone(result['game_stopped'])
        vision.controller.post_click.assert_not_called()

    def test_already_at_stage_is_idempotent(self):
        vision = Mock()
        vision.observe.return_value = observation('stage_ready')
        self.assertTrue(exit_battle(vision)['exit_verified'])
        vision.controller.post_click.assert_not_called()

    def test_stuck_page_is_not_clicked_repeatedly(self):
        vision = Mock()
        vision.observe.return_value = observation('in_battle')
        vision.controller.post_click.return_value = Mock(done=True, succeeded=True)
        with patch('maa_agent.battle_exit.wait'), patch('maa_agent.battle_exit.time.sleep'), patch('maa_agent.battle_exit.time.monotonic', side_effect=[0, 0, 0, 20, 20]):
            result = exit_battle(vision)
        self.assertFalse(result['exit_verified'])
        self.assertEqual(vision.controller.post_click.call_count, 1)

    def test_settlement_animation_retry_is_bounded(self):
        vision = Mock()
        vision.observe.return_value = observation('settlement')
        tick = iter(range(0, 200, 4))
        with patch('maa_agent.battle_exit.wait'), patch('maa_agent.battle_exit.time.sleep'), patch('maa_agent.battle_exit.time.monotonic', side_effect=lambda: next(tick)):
            result = exit_battle(vision)
        self.assertFalse(result['exit_verified'])
        self.assertEqual(vision.controller.post_click.call_count, 3)

    def test_cancel_waits_for_worker_terminal_result(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'request.json').write_text('{}')
            with patch.object(runner, 'run_folder', return_value=folder), patch.object(runner, 'poll', side_effect=[{'executor':'running'}, {'executor':'cancelled'}]), patch.object(runner.time, 'sleep'):
                self.assertEqual(runner.cancel_and_wait('a'), 'cancelled')
            self.assertTrue((folder / 'cancel').exists())

    def test_cancelled_queued_worker_never_initializes_device(self):
        from contextlib import nullcontext
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'request.json').write_text('{}')
            (folder / 'cancel').touch()
            with patch.object(runner, 'run_folder', return_value=folder), patch.object(runner.Settings, 'load'), patch.object(runner, 'device_lock', return_value=nullcontext()), patch('maa_agent.vision.Vision') as vision:
                runner.worker('a')
            vision.assert_not_called()
            self.assertEqual(json.loads((folder / 'result.json').read_text())['executor'], 'cancelled')


if __name__ == '__main__':
    unittest.main()
