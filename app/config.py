import secrets
from envparse import env
from dotenv import load_dotenv

load_dotenv()

DEBUG = env.bool('DEBUG', default=False)

MAX_USER_PROCESSES = env.int('MAX_USER_PROCESSES', default=2)
MAX_FILE_SIZE = env.int('MAX_FILE_SIZE', default=20 * 1024 * 1024)  # 20 MB
MAX_AUDIO_DURATION = env.int('MAX_AUDIO_DURATION', default=6 * 60)  # 6 minutes
MIN_AUDIO_DURATION = env.int('MIN_AUDIO_DURATION', default=3)  # 3 seconds

TG_TOKEN = env.str('TG_TOKEN')
WEBAPP_HOST = env.str('WEBAPP_HOST', default='0.0.0.0')
WEBAPP_PORT = env.int('WEBAPP_PORT', default=8080)

SECRET_KEY = secrets.token_urlsafe(8)
WEBHOOK_DOMAIN = env.str('WEBHOOK_DOMAIN', default='example.com')
WEBHOOK_BASE_PATH = env.str('WEBHOOK_BASE_PATH', default="/webhook")
WEBHOOK_PATH = f'{WEBHOOK_BASE_PATH}/{SECRET_KEY}'
WEBHOOK_URL = f'https://{WEBHOOK_DOMAIN}{WEBHOOK_PATH}'

MYSQL_HOST = env.str('MYSQL_HOST', default='localhost')
MYSQL_PORT = env.int('MYSQL_PORT', default=3306)
MYSQL_PASSWORD = env.str('MYSQL_PASSWORD', default='')
MYSQL_USER = env.str('MYSQL_USER', default='')
MYSQL_DB = env.str('MYSQL_DB', default='')

BOT_ADMIN = env.int('BOT_ADMIN', default=0)

CAPSOLVER_API_KEY = env.str('CAPSOLVER_API_KEY', default='')
SERVICE_TURNSTILE_URL = env.str('SERVICE_TURNSTILE_URL', default='')
SERVICE_TURNSTILE_TOKEN = env.str('SERVICE_TURNSTILE_TOKEN', default='')
