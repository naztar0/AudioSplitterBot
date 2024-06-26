import aiohttp
import aiofiles
from urllib.parse import quote

from app.misc import files_dir
from app.utils.file import ensure_dir
from .audio import Audio


SPLITTERS = {
    Audio.VOCALS: 'orion',
    Audio.VOICE: 'orion',
    Audio.DRUM: 'orion',
    Audio.BASS: 'orion',
    Audio.ELECTRIC_GUITAR: 'orion',
    Audio.ACOUSTIC_GUITAR: 'orion',
    Audio.PIANO: 'orion',
    Audio.SYNTHESIZER: 'phoenix',
}


class Api:
    def __init__(self, filename: str, stem: str, level: int = 1, session=aiohttp.ClientSession()):
        self.api_url = 'https://www.lalal.ai/api'
        self.filename = filename
        self.filepath = files_dir / 'original_parts' / filename
        self.stem = stem
        self.level = level
        self.id = None
        self.success = True
        self.error = None
        self.audio = Audio()
        self.session = session

    def __repr__(self):
        return f'{self.filepath=}\n{self.id=}\n{self.error=}\n{self.audio=}'

    def content_disposition(self):
        try:
            self.filename.encode('ascii')
            file_expr = f'filename="{self.filename}"'
        except UnicodeEncodeError:
            quoted = quote(self.filename)
            file_expr = f"filename*=utf-8''{quoted}"
        return f'attachment; {file_expr}'

    def handle_response(self, res):
        if res["status"] != "success":
            self.success = False
            self.error = res["error"]

    async def upload_file(self):
        headers = {'Content-Disposition': self.content_disposition()}
        with open(self.filepath, 'rb') as f:
            res = await self.session.post(self.api_url + '/upload/', data=f, headers=headers, timeout=60)
            res = await res.json()
            self.handle_response(res)
        if self.success:
            self.id = res["id"]

    async def process(self):
        data = {
            'id': self.id,
            'filter': self.level,
            'stem': self.stem,
            'splitter': SPLITTERS[self.stem]
        }
        res = await self.session.post(self.api_url + '/preview/', data=data, timeout=10)
        res = await res.json()
        self.handle_response(res)

    async def check(self):
        data = {'id': self.id}
        res = await self.session.post(self.api_url + '/check/', data=data, timeout=10)
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
