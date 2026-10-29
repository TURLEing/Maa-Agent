import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4
from .config import RUNTIME, Settings
from .runner import device_lock, execute, poll, run_folder, start_job, worker
from .state import verdict


def compact(value):
    if isinstance(value, dict):
        return {k:compact(v) for k,v in value.items() if k not in ('words','matches','recognized_text')}
    if isinstance(value,list):
        return [compact(v) for v in value]
    return value


def copilot_request(path):
    path = Path(path).resolve()
    content = json.loads(path.read_text(encoding='utf-8'))
    if not content.get('stage_name') or not content.get('actions'):
        raise ValueError('A copilot stage_name and actions are required')
    # A weak agent must not accidentally submit a task file or external command action.
    allowed = {'Deploy','Retreat','Skill','SkillUsage','SpeedUp','SwitchSpeed','BulletTime','Output','SkillDaemon'}
    if any(a.get('type', 'Deploy') not in allowed for a in content['actions']):
        raise ValueError('Unsupported action type; review this copilot before execution')
    return {'tasks':[{'name':'AgentCopilot','type':'Copilot','params':{
        'filename':str(path),'formation':True,'formation_index':4,'support_unit_usage':0,
        'ignore_requirements':False,'use_sanity_potion':False}}]}, content['stage_name']


def main():
    # Windows' default code page must not corrupt Chinese OCR in JSON clients.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Evidence-based MAA tools. Outputs JSON; never uses computer-use.')
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('observe')
    sub.add_parser('home')
    stage = sub.add_parser('stage',help='Open a stage from its current chapter map')
    stage.add_argument('code')
    nav = sub.add_parser('annihilation')
    nav.add_argument('--expected-stage',required=True)
    run = sub.add_parser('run-copilot')
    run.add_argument('file')
    run.add_argument('--expected-stage',required=True)
    run.add_argument('--expected-kills',type=int,default=400)
    run.add_argument('--timeout',type=int,default=2400)
    resume = sub.add_parser('resume')
    resume.add_argument('--parent',required=True)
    resume.add_argument('--actions',required=True,type=Path)
    resume.add_argument('--timeout',type=int,default=1200)
    query = sub.add_parser('poll')
    query.add_argument('run_id')
    query.add_argument('--observe',action='store_true',help='Attach fresh read-only game observation')
    cancel = sub.add_parser('cancel')
    cancel.add_argument('run_id')
    leave = sub.add_parser('exit-battle', help='Stop the executor, abandon combat, and close settlement')
    leave.add_argument('--run-id', help='Worker to cancel before interacting with the game')
    leave.add_argument('--expected-stage', help='Reopen and verify this stage after exiting')
    verify = sub.add_parser('verify')
    verify.add_argument('--expected-kills',type=int,default=400)
    hidden = sub.add_parser('_worker',help=argparse.SUPPRESS)
    hidden.add_argument('run_id')
    args = parser.parse_args()
    try:
        if args.command == '_worker':
            worker(args.run_id)
            return
        if args.command == 'poll':
            result = poll(args.run_id)
            if args.observe:
                from .vision import Vision
                current = Vision(Settings.load()).observe()
                current['outcome'] = verdict(current,result.get('context',{}).get('expected_kills',400))
                result['current_observation'] = current
        elif args.command == 'cancel':
            folder = run_folder(args.run_id)
            if not (folder / 'request.json').exists():
                raise ValueError('Unknown run')
            (folder / 'cancel').touch()
            result = {'executor':'cancellation_requested','game_stopped':False,'next':'poll_then_observe'}
        elif args.command == 'exit-battle':
            from .battle_exit import exit_battle
            from .runner import cancel_and_wait
            from .vision import Vision
            executor = cancel_and_wait(args.run_id) if args.run_id else None
            folder = RUNTIME / 'navigation' / uuid4().hex
            from .config import write_json
            with device_lock():
                vision = Vision(Settings.load())
                result = exit_battle(vision)
                result['executor'] = executor
                result['evidence_dir'] = str(folder)
                write_json(folder / 'exit.json', result)
                if result['exit_verified'] and args.expected_stage:
                    try:
                        result['stage'] = vision.open_stage(args.expected_stage)
                    except Exception as error:
                        result['error'] = f'exit_succeeded_but_stage_not_verified: {error}'
                write_json(folder / 'exit.json', result)
        elif args.command == 'run-copilot':
            task,stage_id = copilot_request(args.file)
            result = start_job(task, {'kind':'copilot','expected_stage':args.expected_stage,
                'stage_id':stage_id,'expected_kills':args.expected_kills}, args.timeout)
        elif args.command == 'resume':
            parent = json.loads((run_folder(args.parent) / 'request.json').read_text(encoding='utf-8'))
            actions = json.loads(args.actions.read_text(encoding='utf-8'))
            if not isinstance(actions,list) or not actions:
                raise ValueError('Actions must be a nonempty JSON array')
            if any(a.get('type') not in {'Deploy','Retreat','Skill','SkillUsage','SkillDaemon'} for a in actions):
                raise ValueError('Only battle actions are allowed in resume')
            stage = parent['context']['stage_id']
            task = {'tasks':[{'type':'SingleStep','params':{'type':'copilot','subtype':'stage','details':{'stage_name':stage}}},
                {'type':'SingleStep','params':{'type':'copilot','subtype':'action','details':{'actions':actions}}}]}
            context = {**parent['context'],'kind':'resume','parent':args.parent}
            result = start_job(task,context,args.timeout)
        else:
            from .vision import Vision
            settings = Settings.load()
            if args.command in ('observe','verify'):
                # Read-only capture can run while our CLI worker is active.
                result = Vision(settings).observe()
                if args.command == 'verify':
                    result['outcome'] = verdict(result,args.expected_kills)
            else:
                with device_lock():
                    vision = Vision(settings)
                    result = vision.open_stage(args.code) if args.command == 'stage' else vision.home()
                    if args.command == 'annihilation':
                        folder = RUNTIME / 'navigation' / uuid4().hex
                        task = {'tasks':[{'type':'Custom','params':{'task_names':['Terminal-Entry']}},
                                         {'type':'Custom','params':{'task_names':['Annihilation']}}]}
                        execution = execute(settings,task,folder,90)
                        result = vision.observe()
                        result['execution'] = execution
                        result['stage_verified'] = result['state'] == 'stage_ready' and args.expected_stage in '\n'.join(result['stage_text'])
                        if not result['stage_verified']:
                            result['error'] = 'navigation_not_verified: do not start battle'
        print(json.dumps(compact(result),ensure_ascii=False,indent=2))
        if result.get('error'):
            sys.exit(1)
    except Exception as error:
        print(json.dumps({'error':str(error),'next':'inspect_evidence'},ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
