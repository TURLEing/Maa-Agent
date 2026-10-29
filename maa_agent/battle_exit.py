"""Bounded, observed exit from combat; caller owns the device lock."""
import re
import time

from .vision import wait


def exit_action(observation):
    """Return a verified exit target, done, or unknown. Coordinates are 1280x720."""
    words = [w for w in observation.get('words', []) if w.get('score', 0) >= .8]
    text = re.sub(r'\s+', '', ''.join(w['text'] for w in words))
    state = observation['state']
    if '是否放弃行动' in text and ('返还' in text or '恢复' in text):
        button = next((w for w in words if w['text'].replace(' ', '') == '放弃行动'
                       and w['box'][0] > 640 and w['box'][1] > 500), None)
        if button:
            x, y, width, height = button['box']
            return 'confirm_quit', (x + width // 2, y + height // 2)
        return 'unknown', None
    paused = ('PAUSE' in text.upper() or '暂停中' in text) and any(
        re.fullmatch(r'\d+\s*/\s*\d+', w['text'].translate(str.maketrans({'|':'1', 'I':'1', 'l':'1', 'O':'0'}))) and 350 < w['box'][0] < 750
        and w['box'][1] < 100 for w in words)
    if state == 'in_battle' or paused:
        return 'open_quit', (76, 50)
    if state == 'failure' or ('任务失败' in text and '点击画面' in text):
        return 'close_failure', (640, 655)
    if state in ('settlement', 'battle_report'):
        return 'close_settlement', (1200, 620)
    if state in ('stage_ready', 'home', 'terminal'):
        return 'done', None
    if state == 'navigable_page' and any(
        re.fullmatch(r'(?:[A-Z]+\d*|\d+)-\d+', w['text']) for w in words):
        return 'done', None
    return 'unknown', None


def exit_battle(vision, timeout=90):
    deadline = time.monotonic() + timeout
    trace = []
    clicked = {}
    last_click = None
    observation = {}
    while time.monotonic() < deadline:
        observation = vision.observe()
        action, point = exit_action(observation)
        trace.append({'state': observation['state'], 'action': action,
                      'screenshot': observation.get('screenshot')})
        if action == 'done':
            return {'game_stopped': True, 'exit_verified': True,
                    'after': observation, 'steps': trace}
        limit = 3 if action == 'close_settlement' else 1
        if action == 'unknown' or clicked.get(action, 0) >= limit or (
                action in clicked and time.monotonic() - last_click < 3):
            # Loading and stale frames never trigger rapid repeated clicks.
            if last_click is None or time.monotonic() - last_click > 12:
                break
            time.sleep(.5)
            continue
        wait(vision.controller.post_click(*point))
        trace[-1]['clicked'] = True
        clicked[action] = clicked.get(action, 0) + 1
        last_click = time.monotonic()
        time.sleep(1)
    return {'game_stopped': None, 'exit_verified': False,
            'error': 'exit_not_verified: inspect last screenshot; no blind retries',
            'after': observation, 'steps': trace}
