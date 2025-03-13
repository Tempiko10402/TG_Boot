import sqlite3
import threading
import logging

class Database:
    def __init__(self, path: str = 'users.db'):
        """Инициализация базы данных с указанным путем к файлу."""
        self._path = path
        self._local = threading.local()
        logging.info(f"Initializing database at: {self._path}")
        self._create_table()

    def _get_conn(self):
        """Получение или создание подключения к базе данных для текущего потока."""
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self._path)
            self._local.conn.row_factory = sqlite3.Row
            logging.info(f"SQLite version: {sqlite3.sqlite_version}")
        return self._local.conn

    def _execute(self, query: str, args=()):
        """Выполнение SQL-запроса с параметрами и обработкой ошибок."""
        conn = self._get_conn()
        cursor = conn.cursor()
        logging.debug(f"Executing query: {query} with args: {args}")
        try:
            cursor.execute(query, args)
            conn.commit()
        except sqlite3.OperationalError as e:
            logging.error(f"SQLite error: {e}")
            raise
        return cursor

    def _create_table(self):
        """Создание таблиц users и tracking, если они еще не существуют."""
        query1 = '''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'ru',
                name TEXT,
                address TEXT
            )
        '''
        self._execute(query1)

        query2 = '''
            CREATE TABLE IF NOT EXISTS tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        '''
        self._execute(query2)

    def user_exists(self, user_id: int) -> bool:
        """Проверка, существует ли пользователь с заданным user_id."""
        cursor = self._execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
        return bool(cursor.fetchone())

    def add_user(self, user_id: int):
        """Добавление пользователя с базовыми значениями."""
        self._execute('INSERT INTO users (user_id, lang, name, address) VALUES (?, "ru", "", "")', (user_id,))

    def update_lang(self, user_id: int, lang: str):
        """Обновление языка пользователя."""
        self._execute('UPDATE users SET lang = ? WHERE user_id = ?', (lang, user_id))

    def update_name(self, user_id: int, name: str):
        """Обновление имени пользователя."""
        self._execute('UPDATE users SET name = ? WHERE user_id = ?', (name, user_id))

    def update_address(self, user_id: int, address: str):
        """Обновление адреса пользователя."""
        self._execute('UPDATE users SET address = ? WHERE user_id = ?', (address, user_id))

    def get_user(self, user_id: int) -> dict:
        """Получение данных пользователя в виде словаря."""
        cursor = self._execute('SELECT lang, name, address FROM users WHERE user_id = ?', (user_id,))
        data = cursor.fetchone()
        return dict(data) if data else None
    
    def add_tracking_item(self, user_id: int, item: str):
        """Добавление элемента для отслеживания."""
        self._execute('INSERT INTO tracking (user_id, item) VALUES (?, ?)', (user_id, item))

    def get_tracking_items(self, user_id: int) -> list:
        """Получение списка отслеживаемых элементов пользователя."""
        cursor = self._execute('SELECT item FROM tracking WHERE user_id = ?', (user_id,))
        return [row["item"] for row in cursor.fetchall()]

    def remove_tracking_item(self, user_id: int, item: str):
        """Удаление элемента из отслеживания."""
        self._execute('DELETE FROM tracking WHERE user_id = ? AND item = ?', (user_id, item))

if __name__ == "__main__":
    db = Database("test.db")
    db.add_user(1)
    db.update_name(1, "John")
    db.add_tracking_item(1, "Item1")
    print("User data:", db.get_user(1))
    print("Tracking items:", db.get_tracking_items(1))