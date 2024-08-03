import ffmpeg
import logging
import asyncio
from aiohttp import ClientSession
from aiogram import types, enums
from aiogram import exceptions
from app.utils import utils
from app.utils.file import ensure_dir
from app.utils.database_connection import DatabaseConnection
from app.misc import files_dir, ffprobe_cmd
from app import bot
from lalalai import Api


async def process_files(filename, file_id, stem, level, session):
    try:
        api = Api(filename, stem, level, session)
        await api.upload_file()
        logging.debug(f'File {filename} uploaded')
        await api.process()
        logging.debug(f'File {filename} processed')
        while api.success and not api.audio:
            await api.check()
            logging.debug(f'File {filename} checked')
            await asyncio.sleep(3)
        if api.error:
            logging.error(f'Error in file {filename}: {api.error}')
            raise FileNotFoundError
        await api.download()
        logging.debug(f'File {filename} downloaded')
    except FileNotFoundError:
        logging.error(f'File not found')
        utils.set_audiofile_status(file_id, 'error')
        raise
    except TimeoutError:
        logging.error(f'Timeout error')
        raise


async def update_audio():
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute('SELECT a.id, users.user_id, a.title, a.stem, a.level '
                       'FROM audiofiles AS a '
                       'INNER JOIN users ON users.id = a.user_id '
                       'WHERE a.status=\'await\'')
        result = cursor.fetchall()
    logging.debug(f'Audio files to update: {len(result)}')
    for res in result:
        file_id, user_id, title, stem, level = res

        parts = utils.split_file(file_id, files_dir / 'original' / f'{file_id}.mp3')

        if not parts:
            logging.error(f'Error splitting file {file_id}: no parts')
            utils.set_audiofile_status(file_id, 'error')
            continue

        files = [f'{file_id}_{part}.mp3' for part in range(parts)]
        logging.debug(f'File parts to upload: {parts}, {files}')

        try:
            async with ClientSession() as session:
                await asyncio.gather(*(
                    asyncio.create_task(
                        process_files(file, file_id, stem, level, session)
                    ) for file in files))
        except (FileNotFoundError, TimeoutError):
            continue

        result_stem = ensure_dir(files_dir / 'result' / 'stem') / f'{file_id}.mp3'
        result_no_stem = ensure_dir(files_dir / 'result' / 'no_stem') / f'{file_id}.mp3'
        result_parts_stem = ensure_dir(files_dir / 'result_parts' / 'stem')
        result_parts_no_stem = ensure_dir(files_dir / 'result_parts' / 'no_stem')

        try:
            utils.crossfade_merge(result_parts_stem, files, title, result_stem)
            utils.crossfade_merge(result_parts_no_stem, files, title, result_no_stem)
        except RuntimeError as e:
            logging.error(f'Error merging files: {e}')
            utils.set_audiofile_status(file_id, 'error')
            continue

        duration = int(float(ffmpeg.probe(result_stem, ffprobe_cmd)['format']['duration']))
        logging.debug(f'Result duration: {duration}')

        try:
            await bot.send_chat_action(user_id, enums.ChatAction.UPLOAD_DOCUMENT)
            await bot.send_audio(user_id, types.FSInputFile(result_stem, filename=title),
                                 duration=duration, title=title, caption='With stem')
            await bot.send_chat_action(user_id, enums.ChatAction.UPLOAD_DOCUMENT)
            await bot.send_audio(user_id, types.FSInputFile(result_no_stem, filename=title),
                                 duration=duration, title=title, caption='No stem')
        except exceptions.TelegramAPIError as e:
            logging.error(f'Error sending audio: {e}')
        except Exception as e:
            logging.error(f'Error: {e}')
        utils.set_audiofile_status(file_id, 'complete')


async def clear_audio():
    def remove_parts(file_id_, parts_dir_):
        for part in parts_dir_.iterdir():
            if part.name.startswith(f'{file_id_}_'):
                part.unlink(missing_ok=True)

    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute('SELECT a.id FROM audiofiles AS a WHERE status IN (\'error\', \'complete\')')
        result = cursor.fetchall()
    logging.debug(f'Audio files to clear: {len(result)}')
    for res in result:
        file_id = res[0]

        # clear original files
        logging.debug(f'Clearing original file {file_id}')
        original = ensure_dir(files_dir / 'original') / f'{file_id}.mp3'
        original.unlink(missing_ok=True)

        logging.debug(f'Clearing original parts for file {file_id}')
        remove_parts(file_id, ensure_dir(files_dir / 'original_parts'))

        # clear result files
        logging.debug(f'Clearing result files for file {file_id}')
        result_stem = ensure_dir(files_dir / 'result' / 'stem') / f'{file_id}.mp3'
        result_stem.unlink(missing_ok=True)
        result_no_stem = ensure_dir(files_dir / 'result' / 'no_stem') / f'{file_id}.mp3'
        result_no_stem.unlink(missing_ok=True)

        logging.debug(f'Clearing result parts for file {file_id}')
        remove_parts(file_id, ensure_dir(files_dir / 'result_parts' / 'stem'))
        remove_parts(file_id, ensure_dir(files_dir / 'result_parts' / 'no_stem'))

        utils.set_audiofile_status(file_id, 'cleared')


async def main():
    executable = (update_audio, clear_audio)
    while True:
        for exe in executable:
            await utils.exec_protected(exe)
        await asyncio.sleep(5)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
