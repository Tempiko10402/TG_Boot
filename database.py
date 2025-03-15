import sqlite3
import threading

class Database:
    def __init__(self, path: str = 'users.db'):
        self._path = path
        self._local = threading.local()
        self._create_table()

    def _get_conn(self):
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self._path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _execute(self, query: str, args=(), commit=True):
        conn = self._get_conn()
        cursor = conn.cursor()
        print(f"[DEBUG] Executing query: {query}, args: {args}")
        cursor.execute(query, args)
        if commit:
            conn.commit()
        return cursor

    def _create_table(self):
        self._execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'ru',
                name TEXT,
                address TEXT
            )
        ''')

    def user_exists(self, user_id: int) -> bool:
        cursor = self._execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,), commit=False)
        result = bool(cursor.fetchone())
        print(f"[DEBUG] user_exists({user_id}): {result}")
        return result

    def add_user(self, user_id: int):
        self._execute('''
            INSERT OR REPLACE INTO users (user_id, lang, name, address)
            VALUES (?, 'ru', '', '')
        ''', (user_id,))
        print(f"[DEBUG] add_user: Пользователь {user_id} добавлен")

    def update_lang(self, user_id: int, lang: str):
        if not self.user_exists(user_id):
            self.add_user(user_id)
        self._execute('UPDATE users SET lang = ? WHERE user_id = ?', (lang, user_id))
        print(f"[DEBUG] update_lang: Язык для {user_id} обновлён на {lang}")

    def update_name(self, user_id: int, name: str):
        if not self.user_exists(user_id):
            self.add_user(user_id)
        print(f"[DEBUG] update_name: Обновление имени для {user_id} на '{name}'")
        self._execute('UPDATE users SET name = ? WHERE user_id = ?', (name, user_id))
        print(f"[DEBUG] update_name: Имя для {user_id} обновлено")

    def update_address(self, user_id: int, address: str):
        if not self.user_exists(user_id):
            self.add_user(user_id)
        print(f"[DEBUG] update_address: Обновление адреса для {user_id} на '{address}'")
        self._execute('UPDATE users SET address = ? WHERE user_id = ?', (address, user_id))
        print(f"[DEBUG] update_address: Адрес для {user_id} обновлён")

    def get_user(self, user_id: int) -> dict:
        cursor = self._execute('SELECT lang, name, address FROM users WHERE user_id = ?', (user_id,), commit=False)
        data = cursor.fetchone()
        result = dict(data) if data else None
        print(f"[DEBUG] get_user({user_id}): {result}")
        return result

    def close(self):
        if hasattr(self._local, "conn"):
            self._local.conn.close()
            del self._local.conn