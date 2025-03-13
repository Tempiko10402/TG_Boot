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
            self._local.conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
        return self._local.conn

    def _execute(self, query: str, args=()):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(query, args)
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
        cursor = self._execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
        return bool(cursor.fetchone())

    def add_user(self, user_id: int):
        """Добавление пользователя с базовыми значениями"""
        self._execute('''
            INSERT INTO users (user_id, lang, name, address)
            VALUES (?, 'ru', '', '')
        ''', (user_id,))

    def update_lang(self, user_id: int, lang: str):
        self._execute('UPDATE users SET lang = ? WHERE user_id = ?', (lang, user_id))

    def update_name(self, user_id: int, name: str):
        self._execute('UPDATE users SET name = ? WHERE user_id = ?', (name, user_id))

    def update_address(self, user_id: int, address: str):
        self._execute('UPDATE users SET address = ? WHERE user_id = ?', (address, user_id))

    def get_user(self, user_id: int) -> dict:
        cursor = self._execute('SELECT lang, name, address FROM users WHERE user_id = ?', (user_id,))
        data = cursor.fetchone()
        return dict(data) if data else None