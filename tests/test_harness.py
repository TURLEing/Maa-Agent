import tempfile
from pathlib import Path
import json
import unittest
from unittest.mock import Mock, patch
from contextlib import nullcontext
from maa_agent.state import interpret, verdict
from maa_agent.cli import copilot_request
from maa_agent.runner import run_folder
from maa_agent import runner
from maa_agent.vision import Vision


def word(text,x=900,y=100,w=100,score=.99):
    return {'text':text,'box':[x,y,w,25],'score':score}


class StateTests(unittest.TestCase):
    def test_partial_success_is_not_full_clear(self):
        observation = interpret([word('作战简报'),word('已歼灭398',900,400),word('已攻入敌方数2',900,350),word('剩余防御点数8',900,300)])
        self.assertEqual(verdict(observation),'partial_clear')

    def test_report_with_separate_number_boxes(self):
        observation = interpret([word('作战简报'),word('已歼灭',900,400),word('400',1150,400),
                                 word('已攻入敌方数',900,350,w=160),word('0',1150,350)])
        self.assertEqual(verdict(observation),'full_clear')

    def test_battle_400_is_not_settlement(self):
        observation = interpret([word('400/400',550,20)], {'battle':True})
        self.assertEqual(observation['state'],'in_battle')
        self.assertEqual(verdict(observation),'unknown')

    def test_normal_stage_requires_unambiguous_settlement_stars(self):
        self.assertEqual(verdict(interpret([],{'stars_3':True}),44),'full_clear')
        self.assertEqual(verdict(interpret([],{'stars_2':True}),44),'partial_clear')
        self.assertEqual(verdict(interpret([],{'stars_3':True,'stars_2':True}),44),'unknown')

    def test_stage_navigation_accepts_merged_operation_title(self):
        vision = Vision.__new__(Vision)
        vision.observe = Mock(return_value={'state':'stage_ready','stage_text':['PEFTONJT8-3']})
        vision.controller = Mock()
        self.assertTrue(vision.open_stage('JT8-3')['stage_verified'])
        vision.controller.post_click.assert_not_called()
        with self.assertRaisesRegex(ValueError,'different_stage'):
            vision.open_stage('JT8-30')

    def test_stage_navigation_reverses_at_map_edge(self):
        vision = Vision.__new__(Vision)
        end = {'state':'navigable_page','words':[word('END8-1')],'screenshot':'edge.png'}
        target = {'state':'navigable_page','words':[word('H8-1')],'screenshot':'target.png'}
        vision.observe = Mock(side_effect=[end,end,end,target,{'state':'stage_ready','stage_text':['H8-1']}])
        vision.controller = Mock()
        vision.controller.post_swipe.return_value = Mock(done=True,succeeded=True)
        vision.controller.post_click.return_value = Mock(done=True,succeeded=True)
        with patch('maa_agent.vision.time.sleep'):
            self.assertTrue(vision.open_stage('H8-1')['stage_verified'])
        self.assertEqual(vision.controller.post_swipe.call_args_list[-1].args,(300,360,1050,360,500))

    def test_truncated_hard_badge_still_requires_full_title(self):
        for title, succeeds in [('H8-1',True),('H8-2',False)]:
            vision = Vision.__new__(Vision)
            vision.observe = Mock(side_effect=[{'state':'navigable_page','words':[word('H8-')]},
                                              {'state':'stage_ready','stage_text':[title]}])
            vision.controller = Mock()
            vision.controller.post_click.return_value = Mock(done=True,succeeded=True)
            with patch('maa_agent.vision.time.sleep'):
                if succeeds:
                    self.assertTrue(vision.open_stage('H8-1')['stage_verified'])
                else:
                    with self.assertRaisesRegex(ValueError,'different_stage'):
                        vision.open_stage('H8-1')

    def test_missing_or_low_confidence_results_are_unknown(self):
        for words in [[],[word('行动结束')],[word('作战简报'),word('已歼灭400'),word('已攻入敌方数0',score=.2)]]:
            self.assertEqual(verdict(interpret(words)),'unknown')

    def test_map_labels_not_used_as_current_stage(self):
        observation = interpret([word('JT8-2',200,300),word('灰石剧场',900,100),word('开始行动',1100,650),word('地图',1100,400)])
        self.assertEqual(observation['state'],'stage_ready')
        self.assertNotIn('JT8-2',observation['stage_text'])

    def test_support_and_potions_disabled(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp)/'copilot.json'
            file.write_text(json.dumps({'stage_name':'camp_r_34','actions':[{'type':'SkillDaemon'}]}),encoding='utf-8')
            task,stage = copilot_request(file)
            self.assertEqual(stage,'camp_r_34')
            self.assertEqual(task['tasks'][0]['params']['support_unit_usage'],0)
            self.assertFalse(task['tasks'][0]['params']['use_sanity_potion'])
            file.write_text(json.dumps({'stage_name':'x','actions':[{'type':'Command'}]}),encoding='utf-8')
            with self.assertRaises(ValueError):
                copilot_request(file)

    def test_run_id_cannot_escape_directory(self):
        with self.assertRaises(ValueError):
            run_folder('../escape')

    def test_home_refuses_active_battle_without_clicking(self):
        vision = Vision.__new__(Vision)
        vision.observe = Mock(return_value={'state':'in_battle'})
        vision.controller = Mock()
        with self.assertRaisesRegex(ValueError, 'battle_active'):
            vision.home()
        vision.controller.post_click.assert_not_called()

    def test_worker_keeps_unknown_when_executor_finishes_during_battle(self):
        self.worker_case('灰石剧场', 'in_battle', 'unknown', True)

    def test_wrong_stage_never_starts_executor(self):
        self.worker_case('错误关卡', 'in_battle', 'unknown', False)

    def test_worker_waits_through_black_transition_before_verifying(self):
        self.worker_case('灰石剧场', 'settlement', 'full_clear', True, transition=True)

    def worker_case(self, visible_stage, after_state, expected_result, starts, transition=False):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            request = {'context':{'kind':'copilot','expected_stage':'灰石剧场'},'task':{},'timeout':30}
            (folder/'request.json').write_text(json.dumps(request),encoding='utf-8')
            before = {'state':'stage_ready','stage_text':[visible_stage]}
            after = {'state':after_state,'kills':400,'leaks':None}
            if transition:
                after['stars'] = 3
            with patch.object(runner,'run_folder',return_value=folder), \
                 patch.object(runner.Settings,'load'), \
                 patch.object(runner,'device_lock',return_value=nullcontext()), \
                 patch('maa_agent.vision.Vision') as vision, \
                 patch.object(runner,'execute',return_value={'executor':'completed'}) as execute, \
                 patch.object(runner.time,'sleep'):
                vision.return_value.observe.side_effect = [before,{'state':'unknown'},after] if transition else [before,after]
                runner.worker('abc')
                result = json.loads((folder/'result.json').read_text(encoding='utf-8'))
                self.assertEqual(execute.called,starts)
                self.assertEqual(result['game_result'],expected_result)
                self.assertEqual(result['preflight_passed'],starts)
                if starts and not transition:
                    self.assertEqual(result['next'],'monitor_or_resume')
                if transition:
                    self.assertEqual(result['next'],'review_result')


if __name__ == '__main__':
    unittest.main()
