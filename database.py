import sqlite3
import logging

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
        self.migrate_database()

    def create_tables(self):
        """Создает основные таблицы в базе данных."""
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

    def migrate_database(self):
        """Добавляет недостающие колонки в таблицы базы данных."""
        try:
            # Проверяем и добавляем колонку 'language' в таблицу 'users', если она отсутствует
            self.cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in self.cursor.fetchall()]
            if 'language' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'ru'")
                self.conn.commit()
                logger.info("Column 'language' added to 'users' table.")
        except Exception as e:
            logger.error(f"Error migrating database: {e}")

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

    def set_user_language(self, user_id, language):
        """Устанавливает язык пользователя."""
        try:
            self.cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting user language: {e}")
            return False

    def get_user_language(self, user_id):
        """Получает язык пользователя."""
        try:
            self.cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 'ru'  # 'ru' по умолчанию
        except Exception as e:
            logger.error(f"Error getting user language: {e}")
            return 'ru'

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

    def get_item_quantity(self, user_id, product_id):
        """Получает количество определенного товара в корзине пользователя."""
        try:
            self.cursor.execute('''SELECT quantity FROM cart 
                                WHERE user_id = ? AND product_id = ?''',
                                (user_id, product_id))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting item quantity: {e}")
            return 0

    def update_item_quantity(self, user_id, product_id, quantity):
        """Обновляет количество товара в корзине."""
        try:
            if quantity <= 0:
                # Если количество 0 или меньше, удаляем товар из корзины
                self.cursor.execute('''DELETE FROM cart 
                                    WHERE user_id = ? AND product_id = ?''',
                                    (user_id, product_id))
            else:
                # Иначе обновляем количество
                self.cursor.execute('''UPDATE cart SET quantity = ?
                                    WHERE user_id = ? AND product_id = ?''',
                                    (quantity, user_id, product_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating item quantity: {e}")
            return False

    def remove_from_cart(self, user_id, product_id):
        """Удаляет товар из корзины."""
        try:
            self.cursor.execute('''DELETE FROM cart 
                                WHERE user_id = ? AND product_id = ?''',
                                (user_id, product_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing item from cart: {e}")
            return False


# Инициализация базы данных
db = Database()