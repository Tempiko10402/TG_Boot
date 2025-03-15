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
        return bool(cursor.fetchone())

    def add_user(self, user_id: int):
        self._execute('''
            INSERT OR REPLACE INTO users (user_id, lang, name, address)
            VALUES (?, 'ru', '', '')
        ''', (user_id,))

    def update_lang(self, user_id: int, lang: str):
        if not self.user_exists(user_id):
            self.add_user(user_id)
        self._execute('UPDATE users SET lang = ? WHERE user_id = ?', (lang, user_id))
        self._get_conn().commit()

    def update_name(self, user_id: int, name: str):
        if not self.user_exists(user_id):
            self.add_user(user_id)
        print(f"[DEBUG] Updating name for {user_id} to '{name}'")
        self._execute('UPDATE users SET name = ? WHERE user_id = ?', (name, user_id))
        self._get_conn().commit()
        print(f"[DEBUG] Name updated for {user_id}")

    def update_address(self, user_id: int, address: str):
        if not self.user_exists(user_id):
            self.add_user(user_id)
        print(f"[DEBUG] Updating address for {user_id} to '{address}'")
        self._execute('UPDATE users SET address = ? WHERE user_id = ?', (address, user_id))
        self._get_conn().commit()
        print(f"[DEBUG] Address updated for {user_id}")

    def get_user(self, user_id: int) -> dict:
        cursor = self._execute('SELECT lang, name, address FROM users WHERE user_id = ?', (user_id,), commit=False)
        data = cursor.fetchone()
        return dict(data) if data else None

    def close(self):
        if hasattr(self._local, "conn"):
            self._local.conn.close()
            del self._local.conn