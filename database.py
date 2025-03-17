import sqlite3
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import os

class Database:
    def __init__(self):
        self.db_name = 'users.db'
        # Генерируем ключ для шифрования, если его нет
        self.key_file = 'encryption_key.key'
        if not os.path.exists(self.key_file):
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
        with open(self.key_file, 'rb') as f:
            self.key = f.read()
        self.cipher = Fernet(self.key)
        self._init_db()

    def _init_db(self):
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                transaction_id INTEGER,
                file_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bank_stats (
                bank_name TEXT PRIMARY KEY,
                usage_count INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_limits (
                user_id INTEGER PRIMARY KEY,
                request_count INTEGER DEFAULT 0,
                last_request TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def _encrypt(self, data: str) -> str:
        if not data:
            return data
        return self.cipher.encrypt(data.encode()).decode()

    def _decrypt(self, data: str) -> str:
        if not data:
            return data
        return self.cipher.decrypt(data.encode()).decode()

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
        if row:
            return {
                "lang": row[0],
                "name": self._decrypt(row[1]) if row[1] else "",
                "address": self._decrypt(row[2]) if row[2] else ""
            }
        return None

    def update_name(self, user_id, name):
        encrypted_name = self._encrypt(name)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (encrypted_name, user_id))
        conn.commit()
        conn.close()
        print(f"[DEBUG] update_name: Имя для {user_id} обновлено на '{name}'")

    def update_address(self, user_id, address):
        encrypted_address = self._encrypt(address)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET address = ? WHERE user_id = ?", (encrypted_address, user_id))
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
        transaction_id = cursor.lastrowid
        # Обновляем статистику банка
        cursor.execute(
            "INSERT OR REPLACE INTO bank_stats (bank_name, usage_count) "
            "VALUES (?, COALESCE((SELECT usage_count FROM bank_stats WHERE bank_name = ?), 0) + 1)",
            (bank, bank)
        )
        conn.commit()
        conn.close()
        print(f"[DEBUG] add_transaction: Транзакция для {user_id} добавлена (банк: {bank}, сумма: {amount})")
        return transaction_id

    def get_transactions(self, user_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT bank, amount, date FROM transactions WHERE user_id = ? ORDER BY date DESC", (user_id,))
        result = cursor.fetchall()
        conn.close()
        return result

    def add_receipt(self, user_id, transaction_id, file_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO receipts (user_id, transaction_id, file_id) VALUES (?, ?, ?)",
            (user_id, transaction_id, file_id)
        )
        conn.commit()
        conn.close()
        print(f"[DEBUG] add_receipt: Квитанция добавлена для {user_id}, transaction_id: {transaction_id}")

    def check_request_limit(self, user_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT request_count, last_request FROM request_limits WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute(
                "INSERT INTO request_limits (user_id, request_count, last_request) VALUES (?, 1, ?)",
                (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            conn.close()
            return True

        request_count, last_request = row
        last_time = datetime.strptime(last_request, "%Y-%m-%d %H:%M:%S")
        current_time = datetime.now()

        # Сбрасываем счётчик, если прошла минута
        if (current_time - last_time).total_seconds() >= 60:
            cursor.execute(
                "UPDATE request_limits SET request_count = 1, last_request = ? WHERE user_id = ?",
                (current_time.strftime("%Y-%m-%d %H:%M:%S"), user_id)
            )
            conn.commit()
            conn.close()
            return True

        if request_count >= 15:
            conn.close()
            return False

        cursor.execute(
            "UPDATE request_limits SET request_count = request_count + 1, last_request = ? WHERE user_id = ?",
            (current_time.strftime("%Y-%m-%d %H:%M:%S"), user_id)
        )
        conn.commit()
        conn.close()
        return True

    def get_bank_stats(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT bank_name, usage_count FROM bank_stats ORDER BY usage_count DESC")
        result = cursor.fetchall()
        conn.close()
        return result

    def close(self):
        print("[DEBUG] Database closed")