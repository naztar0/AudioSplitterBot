import os
import json
import ffmpeg
import logging
import traceback
import aiohttp
import subprocess
from contextlib import suppress
from time import time
from aiogram import types
from aiogram.types import InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.filters import callback_data
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.exceptions import TelegramAPIError
from aiogram.utils.i18n import gettext as _
from app import bot, config
from app.utils import helper
from app.misc import files_dir, ffmpeg_cmd, ffprobe_cmd
from app.utils.database_connection import DatabaseConnection
from app.utils.file import ensure_dir
from lalalai.audio import Audio


class CallbackData(callback_data.CallbackData, prefix='@'):
    func: int
    value: str


class CallbackFuncs:
    LANG = 0x00
    STEM = 0x01
    LEVEL = 0x02


class ButtonSet(helper.Helper):
    mode = helper.HelperMode.snake_case
    REMOVE = helper.Item()
    INL_LANG = helper.Item()
    INL_MODE = helper.Item()
    INL_LEVEL = helper.Item()

    def __new__(cls, btn_set: helper.Item, args=None, row_width=1):
        if btn_set == cls.REMOVE:
            return ReplyKeyboardRemove()
        if str(btn_set).startswith('inl_'):
            builder = InlineKeyboardBuilder()
        else:
            builder = ReplyKeyboardBuilder()
        if btn_set == cls.INL_LANG:
            args = ((_('english'), 'en'), (_('ukrainian'), 'uk'), (_('russian'), 'ru'))
            builder.add(*(InlineKeyboardButton(
                text=text, callback_data=set_callback(CallbackFuncs.LANG, data)
            ) for text, data in args))
        elif btn_set == cls.INL_MODE:
            row_width = 2
            args = ((_('vocals'), Audio.VOCALS),
                    (_('voice'), Audio.VOICE),
                    (_('drum'), Audio.DRUM),
                    (_('bass'), Audio.BASS),
                    (_('electric_guitar'), Audio.ELECTRIC_GUITAR),
                    (_('acoustic_guitar'), Audio.ACOUSTIC_GUITAR),
                    (_('piano'), Audio.PIANO),
                    (_('synthesizer'), Audio.SYNTHESIZER),
                    (_('strings'), Audio.STRINGS),
                    (_('wind'), Audio.WIND))
            builder.add(*(InlineKeyboardButton(
                text=text, callback_data=set_callback(CallbackFuncs.STEM, data)
            ) for text, data in args))
        elif btn_set == cls.INL_LEVEL:
            args = ((_('low'), Audio.LEVEL_LOW),
                    (_('middle'), Audio.LEVEL_MID),
                    (_('high'), Audio.LEVEL_HIGH))
            builder.add(*(InlineKeyboardButton(
                text=text, callback_data=set_callback(CallbackFuncs.LEVEL, data)
            ) for text, data in args))
        # noinspection PyArgumentList
        return builder.adjust(row_width, repeat=True).as_markup(resize_keyboard=True)


def esc_md(s):
    if s is None:
        return ''
    if isinstance(s, str):
        if not s: return ''
        return s.replace('_', '\\_').replace('*', '\\*').replace('`', "'").replace('[', '\\[')
    if isinstance(s, dict):
        return {key: esc_md(x) for key, x in s.items()}
    if isinstance(s, list):
        return list(map(lambda x: esc_md(x), s))
    if isinstance(s, (int, float, bool)):
        return str(s)
    return None


def set_callback(func, data):
    return CallbackData(func=func, value=json.dumps(data, separators=(',', ':'))).pack()


def get_callback(data):
    try:
        cd = CallbackData.unpack(data)
    except (ValueError, TypeError):
        return None
    if cd.value is None or cd.func is None:
        return None
    return cd.func, json.loads(cd.value)


async def exec_protected(func, *args, **kwargs):
    # noinspection PyBroadException
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        stderr = ''
        if isinstance(e, ffmpeg.Error):
            stderr = e.stderr.decode('utf-8')
            logging.error(f'Error: {stderr}')
        with suppress(TelegramAPIError):
            await bot.send_message(config.BOT_ADMIN, traceback.format_exc()[-4096:])
            if stderr:
                await bot.send_message(config.BOT_ADMIN, stderr[-4096:])


def set_audiofile_status(file_id, status):
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute('UPDATE audiofiles SET status=%s WHERE id=%s', [status, file_id])
        conn.commit()


async def download_file(user_id: int, file: types.Audio, data):
    filename = (file.title or file.file_name or str(int(time())))[:255]

    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute('SELECT id FROM users WHERE user_id=%s', [user_id])
        user_id = cursor.fetchone()[0]
        cursor.execute('INSERT INTO audiofiles (user_id, title, stem, level) '
                       'VALUES (%s, %s, %s, %s)',
                       [user_id, filename, data['stem'], data['level']])
        conn.commit()
        file_id = cursor.lastrowid

    destination_file = ensure_dir(files_dir / 'original') / f'{file_id}.mp3'
    try:
        await bot.download(file, destination_file)
    except aiohttp.client_exceptions.ClientPayloadError as e:
        logging.error(f'Error downloading file: {e}')
        set_audiofile_status(file_id, 'error')
        raise TelegramAPIError
    set_audiofile_status(file_id, 'await')


def split_file(file_id, path):
    duration = float(ffmpeg.probe(path, ffprobe_cmd)['format']['duration'])
    logging.debug(f'Duration: {duration}')
    if duration > config.MAX_AUDIO_DURATION:
        set_audiofile_status(file_id, 'error')
        return None

    parts = (duration + duration // 60) / 60 + 1
    if parts.is_integer():
        parts -= 1
    parts = int(parts)
    logging.debug('Splitting file')

    parts_dir = ensure_dir(files_dir / 'original_parts')

    stream = ffmpeg.input(path)
    for part in range(parts):
        stream.audio \
            .filter('atrim', start=part * 60 - part, duration=60) \
            .output(str(parts_dir / f'{file_id}_{part}.mp3')) \
            .global_args('-loglevel', 'error') \
            .run(str(ffmpeg_cmd), overwrite_output=True)
        logging.debug(f'Part {part} done')
    try:
        last_part_duration = float(ffmpeg.probe(parts_dir / f'{file_id}_{parts - 1}.mp3', ffprobe_cmd)['format']['duration'])
    except ffmpeg.Error:
        return None
    if last_part_duration < 2:
        parts -= 1
    return parts


def recompile_file(file_id):  # recompile file to ensure it's not corrupted
    inp = files_dir / 'original' / f'{file_id}.mp3'
    out = files_dir / 'original' / f'{file_id}_copy.mp3'
    args = [
        '-i', inp,
        '-vn',
        '-c:a', 'libmp3lame',
        '-q:a', '2',
        '-loglevel', 'error',
        out,
    ]
    ffmpeg_command_line(*args)
    inp.unlink()
    out.rename(inp)


def ffmpeg_command_line(*ffmpeg_args):
    p = subprocess.Popen([ffmpeg_cmd, *ffmpeg_args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        raise ffmpeg.Error('ffmpeg', out, err)


def crossfade_merge(result_parts, files, title, result):
    if len(files) == 1:
        os.rename(result_parts / files[0], result)
        return
    args = [item for filename in files for item in ('-i', result_parts / filename)]
    args.append('-filter_complex')
    acrossfade_filter = ''
    count = len(files)
    for i in range(count - 1):
        prefix = f'[{"a" if i else ""}{i}][{i + 1}]'
        suffix = f'[a{i + 1}];' if i < count - 2 else ''
        acrossfade_filter += f'{prefix}acrossfade=d=1:c1=nofade:c2=cub{suffix}'
    args.append(acrossfade_filter)
    args.extend([
        '-c:a', 'libmp3lame',
        '-q:a', '2',
        '-metadata', f'title="{title}"',
        '-loglevel', 'error',
        result,
    ])
    logging.debug(f'ffmpeg {args}')
    ffmpeg_command_line(*args)
