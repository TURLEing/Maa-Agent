"""MaaFramework screenshot/OCR/template matching. Never uses desktop automation."""
from datetime import datetime, timezone
import shutil
import re
import time
from uuid import uuid4
from .config import RUNTIME, write_json
from .state import interpret


def wait(job, seconds=30):
    deadline = time.monotonic() + seconds
    while not job.done:
        if time.monotonic() >= deadline:
            raise TimeoutError('Framework operation timed out; do not blindly repeat inputs')
        time.sleep(.05)
    if not job.succeeded:
        raise RuntimeError('Framework operation failed')
    return job


class Vision:
    def __init__(self, settings):
        from maa.controller import AdbController
        from maa.resource import Resource
        from maa.tasker import Tasker
        from maa.toolkit import Toolkit
        from maa.define import LoggingLevelEnum
        Tasker.set_stdout_level(LoggingLevelEnum.Off)
        self.settings = settings
        bundle = RUNTIME / 'vision'
        model = bundle / 'model/ocr'
        model.mkdir(parents=True, exist_ok=True)
        for src, name in [('det/inference.onnx','det.onnx'), ('rec/inference.onnx','rec.onnx'), ('rec/keys.txt','keys.txt')]:
            source = settings.data / 'resource/PaddleOCR' / src
            target = model / name
            if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
                shutil.copy2(source, target)
        (bundle / 'image').mkdir(exist_ok=True)
        self.templates = {}
        for name, source in {'menu':'QuickSwitch/Menu.png', 'home_entry':'QuickSwitch/Home.png',
                             'battle':'Battle/BattleFlag/BattleOfficiallyBegin.png',
                             'stars_3':'Battle/StageDrops/StageDrops-Stars-3.png',
                             'stars_2':'Battle/StageDrops/StageDrops-Stars-2.png'}.items():
            original = settings.data / 'resource/template' / source
            if original.is_file():
                shutil.copy2(original, bundle / 'image' / f'{name}.png')
                self.templates[name] = f'{name}.png'
        if not (bundle / 'pipeline/observe.json').exists():
            write_json(bundle / 'pipeline/observe.json', {'Observe': {'recognition':'DirectHit','action':'DoNothing'}})
        Toolkit.init_option(str(RUNTIME / 'framework'))
        self.controller = AdbController(settings.adb, settings.device)
        wait(self.controller.post_connection())
        self.resource = Resource()
        wait(self.resource.post_bundle(bundle))
        self.tasker = Tasker()
        self.tasker.bind(self.resource, self.controller)
        if not self.tasker.inited:
            raise RuntimeError('Framework tasker not initialized')

    def recognize(self, kind, params, image):
        task = wait(self.tasker.post_recognition(kind, params, image)).get()
        node = self.tasker.get_node_detail(task.node_id_list[-1])
        return node.recognition

    def match(self, name, image):
        from maa.pipeline import JTemplateMatch
        if name not in self.templates:
            return None
        regions = {'menu':(190,0,160,140), 'home_entry':(0,180,180,190), 'battle':(1100,0,180,100),
                   'stars_3':(50,270,250,100), 'stars_2':(50,270,250,100)}
        result = self.recognize('TemplateMatch', JTemplateMatch(template=[self.templates[name]], threshold=[.9], roi=regions[name]), image)
        return result.raw_detail.get('best') if result.hit else None

    def observe(self):
        from maa.pipeline import JOCR
        from PIL import Image
        image = wait(self.controller.post_screencap()).get()
        if image is None or image.shape[:2] != (720,1280):
            raise ValueError('Expected normalized 1280x720 capture; refusing coordinate assumptions')
        ocr = self.recognize('OCR', JOCR(roi=(0,0,1280,720), threshold=.75), image)
        words = ocr.raw_detail.get('all', [])
        matches = {name:self.match(name,image) for name in self.templates}
        result = interpret(words, {key:bool(value) for key,value in matches.items()})
        if result['state'] == 'stage_ready':
            header = self.recognize('OCR',JOCR(roi=(750,65,500,100),threshold=.8),image)
            for word in header.raw_detail.get('all',[]):
                if word.get('score',0) >= .8 and re.fullmatch(r'(?:[A-Z]+\d*|\d+)-[\d|Il]+',word.get('text','')):
                    prefix,separator,suffix = word['text'].rpartition('-')
                    normalized = prefix + separator + suffix.translate(str.maketrans({'|':'1','I':'1','l':'1'}))
                    words.append({**word,'text':normalized,'source_text':word['text'],'source':'stage_header_ocr'})
            result = interpret(words,{key:bool(value) for key,value in matches.items()})
        if result['state'] == 'navigable_page':
            # Hard-stage red/black badges can disappear in full-screen OCR.
            # A second pass isolates their white text, retaining only full H codes.
            import numpy as np
            white = (image.min(axis=2) > 160) & ((image.max(axis=2).astype(int)-image.min(axis=2)) < 65)
            filtered = np.repeat((white*255).astype('uint8')[:,:,None],3,axis=2)
            extra = self.recognize('OCR',JOCR(roi=(0,100,1280,450),threshold=.85),filtered)
            words.extend(w for w in extra.raw_detail.get('all',[]) if w.get('score',0) >= .85 and re.fullmatch(r'H\d+-\d+',w.get('text','')))
            result = interpret(words,{key:bool(value) for key,value in matches.items()})
        result['matches'] = matches
        result['words'] = words
        result['observed_at'] = datetime.now(timezone.utc).isoformat()
        folder = RUNTIME / 'observations'
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{uuid4().hex}.png'
        Image.fromarray(image[:,:,::-1]).save(path)
        result['screenshot'] = str(path)
        write_json(path.with_suffix('.json'), result)
        return result

    def click_match(self, match):
        if not match or 'box' not in match:
            raise ValueError('No matched target')
        x,y,w,h = match['box']
        wait(self.controller.post_click(x+w//2,y+h//2))

    def open_stage(self, code):
        """Open a stage within the current chapter; never press Start Operation."""
        if not re.fullmatch(r'[A-Z]+\d*-\d+', code):
            raise ValueError('Invalid stage code')
        direction = -1
        previous_codes = None
        repeated = 0
        for attempt in range(18):
            observation = self.observe()
            if observation['state'] == 'stage_ready':
                if any(re.search(re.escape(code) + r'(?!\d)', text) for text in observation['stage_text']):
                    return {**observation, 'stage_verified':True}
                raise ValueError('different_stage_open: return to chapter map before navigation')
            if observation['state'] in ('in_battle','formation','failure','settlement','battle_report'):
                raise ValueError('unsafe_page_for_stage_navigation')
            words = [w for w in observation['words'] if w.get('score',0) >= .85]
            enter = next((w for w in words if w['text'] == '前往章节'),None)
            target = next((w for w in words if w['text'].replace(' ','') == code),None)
            # Stylized hard-stage badges sometimes OCR only the chapter prefix.
            # This is only a candidate click: stage-ready title must still match fully.
            prefix_matches = [w for w in words if w['text'].rstrip('-') == code.split('-')[0]]
            if target is None and len(prefix_matches) == 1:
                target = prefix_matches[0]
            if enter:
                self.click_match(enter)
            elif target:
                self.click_match(target)
            elif any(re.fullmatch(r'(?:[A-Z]+\d*|\d+)-\d+',w['text']) for w in words):
                codes = tuple(sorted(w['text'] for w in words if re.fullmatch(r'(?:[A-Z]+\d*|\d+)-\d+',w['text'])))
                repeated = repeated + 1 if codes == previous_codes else 0
                previous_codes = codes
                if direction == -1 and (repeated >= 2 or attempt >= 7):
                    direction = 1
                    repeated = 0
                elif direction == 1 and repeated >= 2:
                    break
                if attempt == 17:
                    break
                # Search both directions; the requested stage may precede the current one.
                start,end = (1050,300) if direction == -1 else (300,1050)
                wait(self.controller.post_swipe(start,360,end,360,500))
            else:
                raise ValueError(f'chapter_map_not_verified: evidence={observation["screenshot"]}')
            time.sleep(1)
        raise ValueError('stage_navigation_limit: target not verified')

    def home(self):
        for _ in range(5):
            observation = self.observe()
            state = observation['state']
            if state == 'home':
                return observation
            if state == 'in_battle':
                raise ValueError('battle_active: home recovery does not abandon combat')
            if state in ('settlement','battle_report','failure'):
                wait(self.controller.post_click(1200,620))
            elif observation['matches'].get('home_entry'):
                self.click_match(observation['matches']['home_entry'])
            elif observation['matches'].get('menu'):
                self.click_match(observation['matches']['menu'])
            else:
                raise ValueError(f'unknown_page: no safe home target; evidence={observation["screenshot"]}')
            time.sleep(1)
        raise ValueError('recovery_limit: homepage not verified after 5 steps')
