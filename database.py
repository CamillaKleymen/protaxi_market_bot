import sqlite3
import logging
import requests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Работа с БД
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('users.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Создание таблицы пользователей
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            protaxi_id TEXT,
            phone TEXT
        )''')

        # Создание таблицы корзины
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            product_name TEXT,
            product_price REAL,
            quantity INTEGER DEFAULT 1
        )''')
        self.conn.commit()

    def add_user(self, user_id, protaxi_id, phone=None):
        """Добавляет пользователя в базу данных."""
        try:
            self.cursor.execute('''INSERT OR REPLACE INTO users (user_id, protaxi_id, phone) 
                                    VALUES (?, ?, ?)''', (user_id, protaxi_id, phone))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False

    def get_user(self, user_id):
        """Получает пользователя по user_id."""
        try:
            self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def add_to_cart(self, user_id, product_id, product_name, product_price):
        """Добавляет товар в корзину или обновляет количество товара."""
        self.cursor.execute('''SELECT id FROM cart WHERE user_id = ? AND product_id = ?''',
                            (user_id, product_id))
        existing_item = self.cursor.fetchone()

        if existing_item:
            # Если товар уже в корзине, увеличиваем его количество
            self.cursor.execute('''UPDATE cart SET quantity = quantity + 1 WHERE id = ?''',
                                (existing_item[0],))
        else:
            # Если товара нет в корзине, добавляем его
            self.cursor.execute('''INSERT INTO cart (user_id, product_id, product_name, product_price, quantity)
                                    VALUES (?, ?, ?, ?, 1)''', (user_id, product_id, product_name, product_price))
        self.conn.commit()

    def get_cart(self, user_id):
        """Получает содержимое корзины пользователя."""
        self.cursor.execute('''SELECT product_name, product_price, quantity 
                               FROM cart WHERE user_id = ?''', (user_id,))
        return self.cursor.fetchall()

    def clear_cart(self, user_id):
        """Очищает корзину пользователя."""
        self.cursor.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))
        self.conn.commit()


# Инициализация базы данных
db = Database()