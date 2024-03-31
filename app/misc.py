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
