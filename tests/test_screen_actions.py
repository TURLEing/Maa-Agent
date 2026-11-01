import json
import tempfile
import unittest
from pathlib import Path
from maa_agent.cli import copilot_request


class ScreenActionTests(unittest.TestCase):
    def request(self, action):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'copilot.json'
            path.write_text(json.dumps({'stage_name':'example', 'actions':[action]}), encoding='utf-8')
            return copilot_request(path)[0]['tasks'][0]['params']

    def test_screen_actions_keep_executor_restrictions(self):
        for action in ({'type':'Click','rect':[1279,719,1,1]},
                       {'type':'Swipe','begin':[0,0,1,1],'end':[1279,719,1,1],'duration':1000},
                       {'type':'Swipe','begin':[0,0,1,1],'end':[20,20,1,1]}):
            params = self.request(action)
            self.assertEqual(params['support_unit_usage'], 0)
            self.assertFalse(params['use_sanity_potion'])
            self.assertFalse(params['ignore_requirements'])

    def test_rejects_invalid_rectangles(self):
        for rect in (None, {}, '1,2,3,4', [], [0,0,1], [True,0,1,1], [0.,0,1,1],
                     [-1,0,1,1], [0,-1,1,1], [0,0,0,1], [0,0,1,-1],
                     [1280,0,1,1], [0,720,1,1], [1279,0,2,1], [0,719,1,2]):
            with self.subTest(rect=rect), self.assertRaises(ValueError):
                self.request({'type':'Click','rect':rect})
        with self.assertRaises(ValueError):
            self.request({'type':'Click'})

    def test_swipe_checks_both_endpoints_and_duration(self):
        for field in ('begin','end'):
            for rect in (None, [-1,0,1,1], [0,719,1,2]):
                action = {'type':'Swipe','begin':[0,0,1,1],'end':[10,10,1,1]}
                action[field] = rect
                with self.subTest(field=field,rect=rect), self.assertRaises(ValueError):
                    self.request(action)
        for duration in (0,-1,True,1.5,'1000',None):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                self.request({'type':'Swipe','begin':[0,0,1,1],'end':[1,1,1,1],'duration':duration})

    def test_command_stays_forbidden(self):
        with self.assertRaises(ValueError):
            self.request({'type':'Command','command':'echo unwanted'})
