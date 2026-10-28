import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('operator_roster', Path(__file__).resolve().parents[1] / 'scripts/operator_roster.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RosterTests(unittest.TestCase):
    def test_incomplete_latest_scan_is_rejected(self):
        log = 'OperBox: {"what":"OperBoxInfo","details":{"done":true}}\nOperBox: {"what":"OperBoxInfo","details":{"done":false}}'
        with self.assertRaises(ValueError):
            module.completed_scan(log)

    def test_ownership_states_do_not_confuse_untrained_and_missing(self):
        roster = {'operators': [{'id': 'a', 'name': '甲', 'elite': 0}, {'id': 'b', 'name': '乙', 'elite': 2}]}
        all_opers = [{'id': 'c', 'name': '丙', 'own': False}, {'id': 'e', 'name': '戊', 'own': True}]
        self.assertEqual(module.lookup(roster, all_opers, '甲')['status'], 'owned_below_e2')
        self.assertEqual(module.lookup(roster, all_opers, 'b')['status'], 'owned_e2')
        self.assertEqual(module.lookup(roster, all_opers, '丙')['status'], 'not_owned_in_scan')
        self.assertEqual(module.lookup(roster, all_opers, '丁')['status'], 'unknown')
        self.assertEqual(module.lookup(roster, all_opers, '戊')['status'], 'owned_details_unknown')

    def test_prts_entities_and_branch_are_parsed(self):
        parser = module.OperatorParser()
        parser.feed('<div data-char-id="char&#95;1" data-zh="甲" data-profession="先锋" data-subprofession="战术家"></div>')
        self.assertEqual(parser.operators['char_1']['branch'], '战术家')


if __name__ == '__main__':
    unittest.main()
