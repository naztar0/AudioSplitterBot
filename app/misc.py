import os
from pathlib import Path


app_dir: Path = Path(__file__).parent.parent
locales_dir = app_dir / 'locales'
files_dir = app_dir / 'files'

if os.name == 'nt':
    ffmpeg_cmd = app_dir / 'bin' / 'ffmpeg'
    ffprobe_cmd = app_dir / 'bin' / 'ffprobe'
else:
    ffmpeg_cmd = 'ffmpeg'
    ffprobe_cmd = 'ffprobe'

base_headers = {
    'x-request-id': 'lalalai',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
}
