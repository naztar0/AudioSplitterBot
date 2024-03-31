import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.i18n.middleware import I18n
from app.config import TG_TOKEN, DEBUG
from app.misc import locales_dir
from app.utils.middlewares import DBI18nMiddleware


logging.basicConfig(level=logging.DEBUG if DEBUG else logging.WARN)

storage = MemoryStorage()
i18n = I18n(path=locales_dir, default_locale='en', domain='bot')

router = Router()
DBI18nMiddleware(i18n=i18n).setup(router)

dp = Dispatcher(storage=storage)
dp.include_router(router)

bot = Bot(TG_TOKEN)
