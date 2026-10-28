"""Build and query the current-account roster from a completed MAA OperBox scan."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = ROOT / 'data/accounts/current'
CATALOG = ROOT / 'data/catalog/prts-operators.json'
SOURCE = 'https://prts.wiki/w/' + quote('干员一览')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


class OperatorParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.operators = {}

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if tag != 'div' or not fields.get('data-char-id') or not fields.get('data-zh'):
            return
        self.operators[fields['data-char-id']] = {
            'name': fields['data-zh'],
            'profession': fields.get('data-profession'),
            'branch': fields.get('data-subprofession'),
            'position': fields.get('data-position'),
            'tags': (fields.get('data-tag') or '').split(),
            'wiki_url': 'https://prts.wiki/w/' + quote(fields['data-zh']),
        }


def refresh_catalog():
    with urlopen(Request(SOURCE, headers={'User-Agent': 'Maa-Agent-roster/0.1'}), timeout=45) as response:
        raw = response.read()
    parser = OperatorParser()
    parser.feed(raw.decode('utf-8'))
    if len(parser.operators) < 300:
        raise ValueError('PRTS page structure changed or incomplete; refusing catalog update')
    save(CATALOG, {'source': SOURCE, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                   'content_sha256': sha256(raw).hexdigest(), 'operators': parser.operators})


def completed_scan(log):
    decoder = json.JSONDecoder()
    matches = list(re.finditer(r'OperBox: (\{)', log))
    if not matches:
        raise ValueError('No OperBox events found in CLI log; run with -vv')
    event = decoder.raw_decode(log[matches[-1].start(1):])[0]
    if event.get('what') != 'OperBoxInfo' or event['details'].get('done') is not True:
        raise ValueError('Latest scan is incomplete; refusing to overwrite the roster')
    return event


def build_roster(event, catalog, observed_at):
    details = event['details']
    if details.get('done') is not True:
        raise ValueError('Scan must be complete')
    operators = []
    ids = set()
    for operator in details['own_opers']:
        if operator['id'] in ids:
            raise ValueError('Duplicate operator id')
        ids.add(operator['id'])
        if not (operator['own'] and 0 <= operator['elite'] <= 2 and operator['level'] >= 1):
            raise ValueError('Invalid ownership or promotion data')
        metadata = catalog['operators'].get(operator['id'], {})
        operators.append({**operator, 'profession': metadata.get('profession'),
                          'branch': metadata.get('branch'), 'position': metadata.get('position'),
                          'tags': metadata.get('tags', []), 'wiki_url': metadata.get('wiki_url'),
                          'skill_level': None, 'masteries': None, 'modules': None,
                          'metadata_status': 'matched_by_id' if metadata else 'unmatched'})
    operators.sort(key=lambda o: (-o['elite'], -o['rarity'], -o['level'], o['name']))
    unresolved = []
    aliases = []
    for entry in details['all_opers']:
        if not entry.get('own') or entry['id'] in ids:
            continue
        same_name = [o for o in operators if o['name'] == entry['name'] and o['rarity'] == entry['rarity']]
        if len(same_name) == 1:
            aliases.append({'catalog_id': entry['id'], 'observed_id': same_name[0]['id'],
                            'name': entry['name'], 'basis': 'same_name_and_rarity; distinct upstream IDs retained'})
        else:
            unresolved.append(entry)
    return {'schema_version': 1, 'account': {'key': 'current', 'identity_verified': False,
            'description': '当前 MuMu 账号，尚未绑定 UID；切换账号后须另建档案'},
            'observed_at': observed_at, 'scan_complete': True,
            'ownership_source': 'MAA OperBox', 'metadata_source': catalog['source'],
            'catalog_retrieved_at': catalog['retrieved_at'], 'operators': operators,
            'owned_without_details': unresolved,
            'ownership_alias_candidates': aliases,
            'recognition_limitations': ['MAA 图像识别可能误识别；done 仅表示扫描流程完成',
              '技能等级、专精、模组未采集；同分支不代表可直接替换',
              '未识别到某形态不代表账号未解锁该形态；升变需另行核验']}


def lookup(roster, all_opers, name):
    owned = next((o for o in roster['operators'] if name in (o['name'], o['id'])), None)
    if owned:
        return {'status': 'owned_e2' if owned['elite'] >= 2 else 'owned_below_e2', 'operator': owned}
    known = next((o for o in all_opers if name in (o['name'], o['id'])), None)
    if known and known.get('own') is True:
        return {'status': 'owned_details_unknown', 'operator': known}
    if known and known.get('own') is False:
        return {'status': 'not_owned_in_scan', 'operator': known}
    return {'status': 'unknown', 'name': name}


def import_scan(log_path):
    text = log_path.read_text(encoding='utf-8')
    event = completed_scan(text)
    stamp = re.findall(r'\[([^\]]+) INFO \] OperBox:', text)[-1]
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    roster = build_roster(event, catalog, stamp + ' (host local time)')
    if (ACCOUNT / 'roster.json').exists():
        previous = json.loads((ACCOUNT / 'roster.json').read_text(encoding='utf-8'))
        if len(roster['operators']) < len(previous['operators']):
            raise ValueError('Reduced scan coverage (possibly active filters); refusing to replace full roster')
    roster['evidence'] = {'cli_log': str(log_path.resolve().relative_to(ROOT)),
                          'log_sha256': sha256(log_path.read_bytes()).hexdigest(),
                          'raw_scan': 'scan.json'}
    save(ACCOUNT / 'scan.json', event)
    save(ACCOUNT / 'roster.json', roster)
    elite = [o for o in roster['operators'] if o['elite'] >= 2]
    save(ACCOUNT / 'elite2.json', {**{k: v for k, v in roster.items() if k != 'operators'}, 'operators': elite})
    lines = ['# 当前账号精二干员', '', f'扫描时间：{roster["observed_at"]}。精二 {len(elite)} 名；扫描到已拥有 {len(roster["operators"])} 名。',
             '', '等级和精英阶段来自 MAA 截图识别；职业/分支来自 PRTS，按干员 ID 关联。技能专精和模组尚未识别。',
             '', '| 干员 | 星级 | 等级 | 职业 | 分支（副职业） | 标签 |', '|---|---:|---:|---|---|---|']
    for o in elite:
        lines.append(f'| {o["name"]} | {o["rarity"]} | 精二 {o["level"]} | {o["profession"] or "待确认"} | {o["branch"] or "待确认"} | {"、".join(o["tags"])} |')
    lines.extend(['', '## 数据范围', '', '全部已拥有名单见 `roster.json`，精二子集见 `elite2.json`；原始识别结果见 `scan.json`。',
                  '缺员判断应先查询全量名单，区分未拥有、拥有但未精二、识别未知。',
                  '这里的分支不是战术替换保证；还须比较技能、射程、阻挡、费用、时序等条件。',
                  '', f'资料来源：[PRTS 干员一览]({SOURCE})。更新流程见仓库 `docs/operator-roster.md`。'])
    if roster['owned_without_details']:
        lines.extend(['', '## 需要补查', '', '确认拥有但练度详情未识别：' + '、'.join(o['name'] for o in roster['owned_without_details']) + '。在补查前不能保证精二子集无遗漏。'])
    (ACCOUNT / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'owned': len(roster['operators']), 'elite2': len(elite),
                      'elite2_by_profession': dict(Counter(o['profession'] for o in elite)),
                      'unmatched': [o['name'] for o in roster['operators'] if o['metadata_status'] == 'unmatched']}, ensure_ascii=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('refresh-catalog')
    imp = sub.add_parser('import-scan')
    imp.add_argument('log', type=Path)
    query = sub.add_parser('query')
    query.add_argument('name')
    args = parser.parse_args()
    if args.command == 'refresh-catalog':
        refresh_catalog()
    elif args.command == 'import-scan':
        import_scan(args.log)
    else:
        roster = json.loads((ACCOUNT / 'roster.json').read_text(encoding='utf-8'))
        event = json.loads((ACCOUNT / 'scan.json').read_text(encoding='utf-8'))
        print(json.dumps(lookup(roster, event['details']['all_opers'], args.name), ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
