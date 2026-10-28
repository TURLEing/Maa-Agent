"""Pure interpretation of OCR evidence; absence of evidence stays unknown."""
import re


def interpret(words, flags=None):
    flags = flags or {}
    words = [w for w in words if w.get('score', 0) >= .75 and w.get('text')]
    text = '\n'.join(w['text'] for w in words)
    compact = re.sub(r'\s', '', text)
    state = 'unknown'
    if '作战简报' in compact and '已歼灭' in compact:
        state = 'battle_report'
    elif '行动失败' in compact or 'MISSIONFAILED' in compact.upper():
        state = 'failure'
    elif '行动结束' in compact or 'MISSIONRESULTS' in compact.upper():
        state = 'settlement'
    elif flags.get('battle'):
        state = 'in_battle'
    elif flags.get('stars_3') or flags.get('stars_2'):
        state = 'settlement'
    elif all(t in compact for t in ['公开招募', '干员寻访', '仓库']):
        state = 'home'
    elif '开始行动' in compact and ('敌方情报' in compact or '地图' in compact):
        state = 'stage_ready'
    elif '快捷编队' in compact and '开始行动' in compact:
        state = 'formation'
    elif '收起' in compact and '首页' in compact:
        state = 'quick_menu'
    elif '资源收集' in compact or '剿灭作战' in compact and '开始行动' not in compact:
        state = 'terminal'
    if state == 'unknown' and flags.get('menu'):
        state = 'navigable_page'

    def report_number(label):
        for word in words:
            if label not in word['text']:
                continue
            suffix = word['text'].split(label, 1)[1]
            digits = re.search(r'\d+', suffix)
            if digits:
                return int(digits[0])
            x, y, width, height = word['box']
            nearby = [w for w in words if re.fullmatch(r'\d+', w['text'])
                      and w['box'][0] >= x + width - 8
                      and abs(w['box'][1] + w['box'][3]/2 - y - height/2) < 25]
            if nearby:
                return int(min(nearby, key=lambda w: w['box'][0])['text'])
        return None

    result = {'state': state, 'outcome': 'unknown', 'kills': None, 'leaks': None,
              'stars': 3 if flags.get('stars_3') and not flags.get('stars_2') else 2 if flags.get('stars_2') and not flags.get('stars_3') else None,
              'remaining_life': None, 'auto_deploy_unlocked': True if '可以使用代理指挥了' in compact else None,
              'stage_text': [w['text'] for w in words if w['box'][0] > 750 and w['box'][1] < 180],
              'recognized_text': text}
    if state == 'battle_report':
        result.update(kills=report_number('已歼灭'), leaks=report_number('已攻入敌方数'), remaining_life=report_number('剩余防御点数'))
    elif state == 'failure':
        result['outcome'] = 'failed'
    elif state == 'in_battle':
        for w in words:
            match = re.fullmatch(r'(\d+)\s*/\s*(\d+)', w['text'].replace('O','0'))
            if match and 350 < w['box'][0] < 750 and w['box'][1] < 100:
                result.update(kills=int(match[1]), total=int(match[2]))
                break
    return result


def verdict(observation, expected_kills=400):
    if observation['state'] == 'failure':
        return 'failed'
    if observation['state'] == 'settlement':
        if observation.get('stars') == 3:
            return 'full_clear'
        if observation.get('stars') == 2:
            return 'partial_clear'
    if observation['state'] != 'battle_report':
        return 'unknown'
    kills, leaks = observation['kills'], observation['leaks']
    if kills is None or leaks is None:
        return 'unknown'
    if kills == expected_kills and leaks == 0:
        return 'full_clear'
    return 'partial_clear'
