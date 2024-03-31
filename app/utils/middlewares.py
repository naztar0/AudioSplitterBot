from typing import Any, Dict, Optional
from aiogram.types import TelegramObject, User
from aiogram.utils.i18n import SimpleI18nMiddleware, I18n
from app.utils.database_connection import DatabaseConnection


class DBI18nMiddleware(SimpleI18nMiddleware):
    def __init__(
        self,
        i18n: I18n,
        i18n_key: Optional[str] = "i18n",
        middleware_key: str = "i18n_middleware",
    ) -> None:
        super().__init__(i18n=i18n, i18n_key=i18n_key, middleware_key=middleware_key)

    async def get_locale(self, event: TelegramObject, data: Dict[str, Any]) -> str:
        event_from_user: Optional[User] = data.get("event_from_user", None)
        if event_from_user is None:
            return self.i18n.default_locale
        with DatabaseConnection() as db:
            conn, cursor = db
            cursor.execute('SELECT locale FROM users WHERE user_id=%s', [event_from_user.id])
            locale = cursor.fetchone()
            if not locale:
                locale = await super().get_locale(event=event, data=data)
                cursor.execute('INSERT INTO users (user_id, locale) VALUES (%s, %s)', [event_from_user.id, locale])
                conn.commit()
            else:
                locale = locale[0]
        return locale

    async def set_locale(self, user_id: int, locale: str):
        self.i18n.current_locale = locale
        with DatabaseConnection() as db:
            conn, cursor = db
            cursor.execute('UPDATE users SET locale=%s WHERE user_id=%s', [locale, user_id])
            conn.commit()
