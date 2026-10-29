"""Persistent jobs. Process completion and game completion are distinct."""
from contextlib import contextmanager
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
from .config import RUNTIME, Settings, write_json


def run_folder(run_id):
    if not run_id or any(c not in '0123456789abcdef' for c in run_id):
        raise ValueError('Invalid run id')
    return RUNTIME / 'runs' / run_id


@contextmanager
def device_lock():
    RUNTIME.mkdir(exist_ok=True)
    with (RUNTIME / 'device.lock').open('a+b') as file:
        file.seek(0)
        if os.name == 'nt':
            import msvcrt
            if file.read(1) == b'':
                file.write(b'0')
                file.flush()
            file.seek(0)
            try:
                msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise ValueError('device_busy: another harness operation owns the device') from error
        else:
            import fcntl
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            if os.name == 'nt':
                output = subprocess.check_output(['tasklist','/FI','IMAGENAME eq maa.exe','/FO','CSV','/NH'], encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
                if any(row and row[0].lower() == 'maa.exe' for row in csv.reader(output.splitlines())):
                    raise ValueError('device_busy: an external maa.exe is active')
            yield
        finally:
            if os.name == 'nt':
                file.seek(0)
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)


def execute(settings, task, folder, timeout=180):
    """Caller owns device_lock. No shell interpolation and bounded cancellation."""
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / 'task.json', task)
    with (folder / 'cli.log').open('wb') as log:
        process = subprocess.Popen([str(settings.cli), 'run', str(folder / 'task.json'), '--batch', '-v', '-p', settings.profile, '-a', settings.device],
                                   stdout=log, stderr=log, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        deadline = time.monotonic() + timeout
        reason = None
        try:
            while process.poll() is None:
                if (folder / 'cancel').exists() or time.monotonic() > deadline:
                    reason = 'cancelled' if (folder / 'cancel').exists() else 'timed_out'
                    process.terminate()
                    try:
                        process.wait(10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break
                time.sleep(.25)
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait()
    return {'executor': reason or ('completed' if process.returncode == 0 else 'failed'),
            'exit_code': process.returncode,
            'game_result': 'unknown', 'game_stopped': False}


def start_job(task, context, timeout):
    run_id = uuid4().hex
    folder = run_folder(run_id)
    if context['kind'] == 'copilot':
        original = Path(task['tasks'][0]['params']['filename'])
        write_json(folder / 'copilot.json', json.loads(original.read_text(encoding='utf-8')))
        task['tasks'][0]['params']['filename'] = str(folder / 'copilot.json')
    write_json(folder / 'request.json', {'task':task, 'context':context, 'timeout':timeout})
    write_json(folder / 'result.json', {'run_id':run_id,'executor':'queued','game_result':'unknown'})
    with (folder / 'worker.log').open('wb') as output:
        process = subprocess.Popen([sys.executable,'-m','maa_agent','_worker',run_id], stdout=output, stderr=output,
                                   creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0), cwd=str(Path(__file__).resolve().parents[1]))
    return {'run_id':run_id, 'executor':'queued', 'worker_pid':process.pid, 'next':'poll'}


def worker(run_id):
    from .vision import Vision
    from .state import verdict
    folder = run_folder(run_id)
    request = json.loads((folder / 'request.json').read_text(encoding='utf-8'))
    result = {'run_id':run_id,'executor':'starting','game_result':'unknown'}
    try:
        settings = Settings.load()
        with device_lock():
            if (folder / 'cancel').exists():
                result.update(executor='cancelled', game_stopped=False)
                return
            vision = Vision(settings)
            before = vision.observe()
            context = request['context']
            result.update(before=before, context=context, preflight_passed=False)
            if context['kind'] == 'copilot':
                if before['state'] != 'stage_ready' or context['expected_stage'] not in '\n'.join(before['stage_text']):
                    raise ValueError('precondition_failed: expected stage must be visible on stage-ready page')
            elif context['kind'] == 'resume':
                parent = json.loads((run_folder(context['parent']) / 'request.json').read_text(encoding='utf-8'))
                parent_result = poll(context['parent'])
                if not parent_result.get('preflight_passed') or parent_result['executor'] not in ('completed','failed','cancelled','timed_out'):
                    raise ValueError('precondition_failed: parent must have passed preflight and stopped its executor')
                if parent['context'].get('stage_id') != context['stage_id'] or before['state'] != 'in_battle':
                    raise ValueError('precondition_failed: resume requires active battle and matching parent stage')
            result.update(executor='running', preflight_passed=True)
            write_json(folder / 'result.json', result)
            if (folder / 'cancel').exists():
                result.update(executor='cancelled', game_stopped=False)
                return
            result.update(execute(settings, request['task'], folder, request['timeout']))
            after = vision.observe()
            # A successful CLI can exit during the black transition before settlement.
            for _ in range(3):
                if result['executor'] != 'completed' or after['state'] != 'unknown':
                    break
                time.sleep(2)
                after = vision.observe()
            result['after'] = after
            result['game_result'] = verdict(after, context.get('expected_kills',400))
            if after['state'] == 'in_battle':
                result['next'] = 'monitor_or_resume'
            elif result['game_result'] == 'unknown':
                result['next'] = 'observe_or_verify'
            else:
                result['next'] = 'review_result'
    except Exception as error:
        result.update(executor='error', error=str(error), next='inspect_evidence')
    finally:
        write_json(folder / 'result.json', result)


def poll(run_id):
    folder = run_folder(run_id)
    result = json.loads((folder / 'result.json').read_text(encoding='utf-8'))
    if (folder / 'cli.log').exists():
        result['recent_events'] = (folder / 'cli.log').read_text(encoding='utf-8',errors='replace').splitlines()[-12:]
    result['evidence_dir'] = str(folder)
    if (folder / 'verification.json').exists():
        result['verification'] = json.loads((folder / 'verification.json').read_text(encoding='utf-8'))
    return result


def cancel_and_wait(run_id, timeout=30):
    """Wait for the worker's terminal result before another device operation."""
    folder = run_folder(run_id)
    if not (folder / 'request.json').exists():
        raise ValueError('Unknown run')
    (folder / 'cancel').touch()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = poll(run_id)
        if result['executor'] in ('completed', 'failed', 'cancelled', 'timed_out', 'error'):
            return result['executor']
        time.sleep(.25)
    raise TimeoutError('executor_stop_not_verified: no game inputs sent')
