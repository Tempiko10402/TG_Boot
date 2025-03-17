import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.db_name = 'users.db'
        self._init_db()

    def _init_db(self):
        # Создаём таблицы при инициализации
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'ru',
                name TEXT,
                address TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bank TEXT,
                amount REAL,
                date TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        conn.commit()
        conn.close()

    def _get_connection(self):
        # Создаём новое соединение для каждого вызова
        return sqlite3.connect(self.db_name)

    def user_exists(self, user_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone() is not None
        conn.close()
        return result

    def add_user(self, user_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO users (user_id, lang, name, address) VALUES (?, 'ru', '', '')",
            (user_id,)
        )
        conn.commit()
        conn.close()
        print(f"[DEBUG] add_user: Пользователь {user_id} добавлен")

    def get_user(self, user_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT lang, name, address FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return {"lang": row[0], "name": row[1], "address": row[2]} if row else None

    def update_name(self, user_id, name):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (name, user_id))
        conn.commit()
        conn.close()
        print(f"[DEBUG] update_name: Имя для {user_id} обновлено на '{name}'")

    def update_address(self, user_id, address):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET address = ? WHERE user_id = ?", (address, user_id))
        conn.commit()
        conn.close()
        print(f"[DEBUG] update_address: Адрес для {user_id} обновлён на '{address}'")

    def update_lang(self, user_id, lang):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
        conn.commit()
        conn.close()
        print(f"[DEBUG] update_lang: Язык для {user_id} обновлён на '{lang}'")

    def add_transaction(self, user_id, bank, amount):
        conn = self._get_connection()
        cursor = conn.cursor()
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO transactions (user_id, bank, amount, date) VALUES (?, ?, ?, ?)",
            (user_id, bank, amount, date)
        )
        conn.commit()
        conn.close()
        print(f"[DEBUG] add_transaction: Транзакция для {user_id} добавлена (банк: {bank}, сумма: {amount})")

    def get_transactions(self, user_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT bank, amount, date FROM transactions WHERE user_id = ? ORDER BY date DESC", (user_id,))
        result = cursor.fetchall()
        conn.close()
        return result

    def close(self):
        # Больше не нужно закрывать соединение здесь, так как мы создаём его в каждом методе
        print("[DEBUG] Database closed")