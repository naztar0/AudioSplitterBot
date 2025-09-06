import aiofiles

from app.misc import files_dir
from app.utils.file import ensure_dir
from .audio import Audio


SPLITTERS = {
    Audio.VOCALS: 'perseus',
    Audio.VOICE: 'perseus',
    Audio.DRUM: 'perseus',
    Audio.BASS: 'perseus',
    Audio.ELECTRIC_GUITAR: 'perseus',
    Audio.ACOUSTIC_GUITAR: 'perseus',
    Audio.PIANO: 'perseus',
    Audio.SYNTHESIZER: 'phoenix',
    Audio.STRINGS: 'phoenix',
    Audio.WIND: 'phoenix',
}

ENHANCE = {
    Audio.VOCALS: 'true',
    Audio.VOICE: 'false',
    Audio.DRUM: 'true',
    Audio.BASS: 'false',
    Audio.ELECTRIC_GUITAR: 'true',
    Audio.ACOUSTIC_GUITAR: 'true',
    Audio.PIANO: 'true',
    Audio.SYNTHESIZER: 'false',
    Audio.STRINGS: 'false',
    Audio.WIND: 'false',
}


class Api:
    def __init__(self, filename: str, stem: str, level: int = 1, session=None, captcha=None):
        self.api_url = 'https://www.lalal.ai/api'
        self.filename = filename
        self.filepath = files_dir / 'original_parts' / filename
        self.stem = stem
        self.level = level
        self.id = None
        self.upload_id = None
        self.success = True
        self.error = None
        self.audio = Audio()
        self.session = session
        self.captcha = captcha

    def __repr__(self):
        return f'{self.filepath=}\n{self.id=}\n{self.success=}\n{self.error=}\n{self.audio=}'

    def handle_response(self, res):
        if res['status'] != 'success':
            self.success = False
            self.error = res['error']
        if self.id is not None and 'result' in res:
            task = res['result'][self.id]['task']
            if task['state'] == 'error':
                self.success = False
                self.error = task['error']

    async def upload_file(self):
        url = await self._create_upload()
        if not url:
            return
        await self._upload_file(url)
        if not self.success:
            return
        await self._complete_upload()

    async def _create_upload(self):
        data = {
            'file_name': self.filename,
            'parts_count': 1
        }
        res = await self.session.post(self.api_url + '/upload/multipart/create/', data=data)
        res = await res.json()
        self.handle_response(res)
        if not self.success:
            return None
        self.id = res['file_id']
        self.upload_id = res['upload_id']
        return res['upload_urls'][0]

    async def _upload_file(self, upload_url):
        headers = {'content-type': ''}
        with open(self.filepath, 'rb') as f:
            res = await self.session.put(upload_url, data=f, headers=headers, timeout=60)
        self.success = res.status == 200

    async def _complete_upload(self):
        data = {
            'file_id': self.id,
            'upload_id': self.upload_id
        }
        res = await self.session.post(self.api_url + '/upload/multipart/complete/', data=data)
        res = await res.json()
        self.handle_response(res)

    async def process(self):
        data = {
            'id': self.id,
            'stem': self.stem,
            'splitter': SPLITTERS[self.stem],
            'enhanced_processing_enabled': ENHANCE[self.stem],
            'dereverb_enabled': 'false',
            'noise_canceling_level': self.level,
            'with_segments': 'false',
            'turnstile-response': self.captcha
        }
        res = await self.session.post(self.api_url + '/preview/', data=data)
        res = await res.json()
        self.handle_response(res)

    async def check(self):
        data = {'id': self.id}
        res = await self.session.post(self.api_url + '/check/', data=data)
        res = await res.json()
        self.handle_response(res)
        if not self.success:
            return
        preview = res['result'][self.id]['preview']
        if not preview:
            return
        self.audio.stem = preview['stem_track']
        self.audio.no_stem = preview['back_track']

    async def _download(self, url, filename):
        async with self.session.get(url) as res:
            async with aiofiles.open(filename, 'wb') as f:
                while chunk := await res.content.read(1024):
                    await f.write(chunk)

    async def download(self):
        folder = files_dir / 'result_parts'

        await self._download(self.audio.stem, ensure_dir(folder / 'stem') / self.filename)
        await self._download(self.audio.no_stem, ensure_dir(folder / 'no_stem') / self.filename)
