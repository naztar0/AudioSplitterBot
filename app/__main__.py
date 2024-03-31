from app import config
from app.bot import start_pooling, start_webhook


if __name__ == '__main__':
    if config.DEBUG:
        start_pooling()
    else:
        start_webhook()
