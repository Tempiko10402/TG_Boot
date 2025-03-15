import sqlite3
conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM users WHERE user_id = ?", (1406374607,))
print(cursor.fetchone())
conn.close()