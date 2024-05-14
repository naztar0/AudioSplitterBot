import logging
from asyncio import get_event_loop
from aiohttp import web
from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.utils.i18n import gettext as _
from aiogram.exceptions import TelegramAPIError

from app import config, bot, router, dp
from app.utils.database_connection import DatabaseConnection
from app.utils.utils import get_callback, CallbackFuncs, ButtonSet, download_file
from app.utils.middlewares import DBI18nMiddleware


class Form(StatesGroup):
    lang = State()
    stem = State()
    level = State()
    file = State()
    processing = State()


@router.message(Command('language'))
async def message_handler(message: types.Message, state: FSMContext):
    await state.set_state(Form.lang)
    await message.answer(_('select_language'), reply_markup=ButtonSet(ButtonSet.INL_LANG))


@router.callback_query(Form.lang)
async def callback_query_handler(callback_query: types.CallbackQuery, i18n_middleware: DBI18nMiddleware):
    data = get_callback(callback_query.data)
    if data is None:
        return
    func, data = data
    if func == CallbackFuncs.LANG:
        await i18n_middleware.set_locale(callback_query.from_user.id, data)
        await callback_query.message.edit_text(_('language_changed'))


@router.message(Command('start'))
async def message_handler(message: types.Message, state: FSMContext):
    await message.answer(_('start_message'))
    await send_menu(message, state)


@router.message(F.text)
async def message_handler(message: types.Message, state: FSMContext):
    await send_menu(message, state)


async def send_menu(message: types.Message, state: FSMContext):
    await state.set_state(Form.stem)
    await message.answer(_('choose_mode'), reply_markup=ButtonSet(ButtonSet.INL_MODE))


@router.message(F.audio, Form.file)
async def message_handler(message: types.Message, state: FSMContext):
    await set_audiofile(message, state)


@router.callback_query(Form.stem)
async def callback_query_handler(callback_query: types.CallbackQuery, state: FSMContext):
    data = get_callback(callback_query.data)
    if data is None:
        return
    func, data = data
    if func == CallbackFuncs.STEM:
        await set_stem(callback_query.message, data, state)


@router.callback_query(Form.level)
async def callback_query_handler(callback_query: types.CallbackQuery, state: FSMContext):
    data = get_callback(callback_query.data)
    if data is None:
        return
    func, data = data
    if func == CallbackFuncs.LEVEL:
        await set_level(callback_query.message, data, state)


async def set_stem(message, data, state):
    await state.update_data({'stem': data})
    await state.set_state(Form.level)
    await message.edit_text(_('choose_level'), reply_markup=ButtonSet(ButtonSet.INL_LEVEL))


async def set_level(message, data, state):
    await state.update_data({'level': data})
    await state.set_state(Form.file)
    await message.edit_text(_('send_audiofile'))


async def set_audiofile(message, state):
    if message.audio.file_size > config.MAX_FILE_SIZE:
        return await message.reply(_('file_too_big'))
    if message.audio.duration > config.MAX_AUDIO_DURATION:
        return await message.reply(_('file_too_long'))
    with DatabaseConnection() as db:
        conn, cursor = db
        cursor.execute('SELECT COUNT(a.id) '
                       'FROM audiofiles AS a '
                       'INNER JOIN users ON users.id = a.user_id '
                       'WHERE a.status IN (\'init\', \'await\') AND users.user_id=%s',
                       [message.chat.id])
        user_processes = cursor.fetchone()[0]
    if user_processes >= config.MAX_USER_PROCESSES:
        return await message.answer(_('max_processes'))
    await state.set_state(Form.processing)
    await message.answer(_('processing'))
    try:
        await download_file(message.chat.id, message.audio, await state.get_data())
    except TelegramAPIError:
        await message.answer(_('error_processing'))


async def on_startup():
    await bot.set_webhook(config.WEBHOOK_URL)
    info = await bot.get_webhook_info()
    logging.warning(f'URL: {info.url}\nPending update count: {info.pending_update_count}')


async def on_shutdown():
    await bot.delete_webhook()


def start_pooling():
    loop = get_event_loop()
    loop.run_until_complete(dp.start_polling(bot, skip_updates=True))


def start_webhook():
    app = web.Application()
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=config.WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host=config.WEBAPP_HOST, port=config.WEBAPP_PORT)
