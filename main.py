import logging
import smtplib
import sqlite3
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from database import db
from buttons import Keyboard
from lang import Languages

import aiohttp
import asyncio
import requests
import telebot
from config import Config
from telebot import types

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# global variable => bot token
bot = telebot.TeleBot(Config.API_TOKEN)

# Состояния пользователей
user_states = {}


# Добавим функцию для выбора языка перед авторизацией
def choose_language(message):
    try:
        user_id = message.from_user.id
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        russian_btn = types.KeyboardButton("🇷🇺 Русский")
        uzbek_btn = types.KeyboardButton("🇺🇿 O'zbek")
        markup.add(russian_btn, uzbek_btn)

        bot.send_message(
            message.chat.id,
            "Выберите язык / Tilni tanlang:",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, set_user_language)
    except Exception as e:
        logger.error(f"Language choose error: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте позже.")


def set_user_language(message):
    try:
        user_id = message.from_user.id
        language = 'ru' if message.text == "🇷🇺 Русский" else 'uz'

        db.set_user_language(user_id, language)

        bot.send_message(
            message.chat.id,
            Languages.get_string(language, 'welcome'),
            reply_markup=types.ReplyKeyboardRemove()
        )
        user_states[user_id] = {'state': 'waiting_for_id', 'language': language}
        bot.register_next_step_handler(message, process_protaxi_id)
    except Exception as e:
        logger.error(f"Set user language error: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте позже.")


# Функции проверки API
async def check_protaxi_id(protaxi_id):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{Config.CHECK_ID_URL}?id={protaxi_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'success': data.get('success') is True,
                        'balance': data.get('balance', 0)  # Get balance from JSON response
                    }
                return {'success': False, 'balance': 0}
    except Exception as e:
        logger.error(f"Error checking ProTaxi ID: {e}")
        return {'success': False, 'balance': 0}


async def verify_login(protaxi_id, password):
    """Проверка логина через API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{Config.LOGIN_URL}?id={protaxi_id}&password={password}") as response:
                if response.status == 200:
                    data = await response.json()
                    # Проверяем наличие объекта success в ответе
                    return 'success' in data and isinstance(data['success'], dict)
                return False
    except Exception as e:
        logger.error(f"Error verifying login: {e}")
        return False




# Старт бота и регистрация
@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        user = db.get_user(user_id)

        if not user:
            choose_language(message)
        else:
            user_language = db.get_user_language(user_id)
            show_main_menu(message.chat.id, user_language)
    except Exception as e:
        logger.error(f"Start error: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте позже.")

# Модифицируем process_protaxi_id
def process_protaxi_id(message):
    try:
        user_id = message.from_user.id
        protaxi_id = message.text.strip()
        language = user_states[user_id]['language']

        result = asyncio.run(check_protaxi_id(protaxi_id))
        if result['success']:
            user_states[user_id].update({
                'state': 'waiting_for_password',
                'protaxi_id': protaxi_id,
                'balance': result['balance']
            })
            bot.send_message(
                message.chat.id,
                Languages.get_string(language, 'id_confirmed')
            )
            bot.register_next_step_handler(message, process_password)
        else:
            bot.send_message(
                message.chat.id,
                Languages.get_string(language, 'invalid_id')
            )
            bot.register_next_step_handler(message, process_protaxi_id)
    except Exception as e:
        logger.error(f"Process ProTaxi ID error: {e}")
        bot.send_message(message.chat.id, Languages.get_string('ru', 'restart'))

# Модифицируем другие функции аналогично, используя Languages.get_string()
def process_password(message):
    try:
        user_id = message.from_user.id
        if user_id not in user_states:
            bot.send_message(message.chat.id, Languages.get_string('ru', 'session_error'))
            return

        password = message.text.strip()
        protaxi_id = user_states[user_id]['protaxi_id']
        balance = user_states[user_id]['balance']
        language = user_states[user_id]['language']

        if asyncio.run(verify_login(protaxi_id, password)):
            if not db.get_user(user_id):
                db.add_user(user_id, protaxi_id, f"ProTaxi_{protaxi_id}")

            del user_states[user_id]

            bot.send_message(
                message.chat.id,
                Languages.get_string(language, 'auth_success').format(balance)
            )
            show_main_menu(message.chat.id, language)
        else:
            bot.send_message(
                message.chat.id,
                Languages.get_string(language, 'invalid_password')
            )
            bot.register_next_step_handler(message, process_password)
    except Exception as e:
        logger.error(f"Process password error: {e}")
        bot.send_message(message.chat.id, Languages.get_string('ru', 'restart'))


async def get_current_balance(protaxi_id):
    result = await check_protaxi_id(protaxi_id)
    return result['balance']

# API функции
async def fetch_product_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                logger.error(f"Ошибка при получении данных с {url}: {response.status}")
                return None


async def fetch_all_products():
    data = await fetch_product_data(Config.PRODUCTS_API_URL)
    return data


def fetch_all_categories():
    try:
        response = requests.get(Config.CATEGORIES_API_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch categories: {e}")
        return []


async def fetch_products_by_category(category_id):
    url = f"{Config.PRODUCTS_API_URL}?category_id={category_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Error fetching products for category {category_id}: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Exception fetching products: {e}")
        return None


# Email функции
from datetime import datetime

def format_order_email(user_id, cart_items, total):
    user_info = db.get_user(user_id)
    if not user_info:
        return None

    order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message_text = f"""
Новый заказ #{user_id}
Дата и время: {order_time}

Информация о покупателе:
-------------------------
ProTaxi ID: {user_info[1]}

Состав заказа:
-------------------------
"""
    # Форматируем каждый элемент корзины
    for name, price, quantity in cart_items:
        item_total = price * quantity
        message_text += f"{name.ljust(25)} {str(quantity).rjust(3)} шт. × {str(price).rjust(8)} ProCoin = {str(item_total).rjust(8)} ProCoin\n"

    # Итоговая сумма заказа
    message_text += f"\n-------------------------\nИтоговая сумма заказа: {str(total).rjust(8)} ProCoin"

    return message_text


def send_order_email(user_id, cart_items, total):
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.EMAIL_HOST_USER
        msg['To'] = Config.EMAIL_RECIPIENT
        msg['Subject'] = f'Новый заказ #{user_id} от {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

        message_text = format_order_email(user_id, cart_items, total)
        if not message_text:
            logger.error(f"Failed to format email for user {user_id}")
            return False

        msg.attach(MIMEText(message_text, 'plain'))

        with smtplib.SMTP(Config.EMAIL_HOST, Config.EMAIL_PORT) as server:
            server.starttls()
            server.login(Config.EMAIL_HOST_USER, Config.EMAIL_HOST_PASSWORD)
            server.send_message(msg)

        logger.info(f"Order email sent successfully for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send order email: {e}")
        return False


# Модифицируем show_main_menu
def show_main_menu(chat_id, language='ru'):
    try:
        bot.send_message(
            chat_id,
            Languages.get_string(language, 'main_menu'),
            reply_markup=Keyboard.main_menu(language)
        )
    except Exception as e:
        logger.error(f"Show main menu error: {e}")
        bot.send_message(chat_id, Languages.get_string('ru', 'error'))


# Обработчик callback-запросов
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        user_id = call.from_user.id

        async def get_user_balance(protaxi_id):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{Config.CHECK_ID_URL}?id={protaxi_id}") as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get('balance', 0)
                        return 0
            except Exception as e:
                logger.error(f"Error getting user balance: {e}")
                return 0

        if call.data == "main_menu":
            try:
                bot.edit_message_text(
                    "📋 Главное меню:",
                    chat_id,
                    message_id,
                    reply_markup=Keyboard.main_menu()
                )
            except telebot.apihelper.ApiException:
                bot.send_message(
                    chat_id,
                    "📋 Главное меню:",
                    reply_markup=Keyboard.main_menu()
                )

        elif call.data == "categories":
            categories = fetch_all_categories()
            if not categories:
                bot.answer_callback_query(call.id, "😔 Категории временно недоступны")
                return

            markup = types.InlineKeyboardMarkup(row_width=1)
            for category in categories:
                category_button = types.InlineKeyboardButton(
                    category['name'],
                    callback_data=f"show_products_{category['id']}"
                )
                markup.add(category_button)
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))

            try:
                bot.edit_message_text(
                    "📂 Выберите категорию:",
                    chat_id,
                    message_id,
                    reply_markup=markup
                )
            except telebot.apihelper.ApiException:
                bot.send_message(
                    chat_id,
                    "📂 Выберите категорию:",
                    reply_markup=markup
                )


        elif call.data.startswith("show_products_"):
            category_id = call.data.split("_")[2]
            products = asyncio.run(fetch_products_by_category(category_id))

            if not products:
                bot.edit_message_text(
                    "😔 К сожалению, товары в данной категории временно недоступны.",
                    chat_id,
                    message_id,
                    reply_markup=Keyboard.main_menu()
                )
                return

            bot.delete_message(chat_id, message_id)

            for product in products:
                try:
                    if 'image' in product and product['image']:
                        text = (f"📦 {product['name']}\n"
                                f"💰 Цена: {product['price']} {product['currency']}\n")
                        markup = types.InlineKeyboardMarkup(row_width=2)
                        markup.add(
                            types.InlineKeyboardButton(
                                "✅ Добавить в корзину",
                                callback_data=f"add_{category_id}_{product['id']}"
                            ),

                            types.InlineKeyboardButton(
                                "🛒 Корзина",
                                callback_data="cart"
                            ),
                            #
                            # types.InlineKeyboardButton(
                            #     "🛒 Корзина",
                            #     callback_data="cart"
                            # ),
                            types.InlineKeyboardButton(
                                "◀️ Вернуться назад",
                                callback_data="categories"
                            )
                        )

                        bot.send_photo(
                            chat_id,
                            photo=product['image'],
                            caption=text,
                            reply_markup=markup
                        )

                    else:
                        text = (f"📦 {product['name']}\n"
                                f"💰 Цена: {product['price']} {product['currency']}\n")

                        markup = types.InlineKeyboardMarkup(row_width=2)
                        markup.add(
                            types.InlineKeyboardButton(
                                "✅ Добавить в корзину",
                                callback_data=f"add_{category_id}_{product['id']}"
                            ),

                            types.InlineKeyboardButton(
                                "🛒 Корзина",
                                callback_data="cart"
                            ),
                            # types.InlineKeyboardButton(
                            #     "🛒 Корзина",
                            #     callback_data="cart"
                            # ),
                            types.InlineKeyboardButton(
                                "◀️ К категориям",
                                callback_data="categories"
                            )

                        )

                        bot.send_message(chat_id, text, reply_markup=markup)

                except Exception as e:
                    logger.error(f"Error sending product with image: {e}")

                    text = (f"📦 {product['name']}\n"
                            f"💰 Цена: {product['price']} {product['currency']}\n")

                    markup = types.InlineKeyboardMarkup(row_width=2)

                    markup.add(
                        types.InlineKeyboardButton(
                            "✅ Добавить в корзину",
                            callback_data=f"add_{category_id}_{product['id']}"
                        ),

                        types.InlineKeyboardButton(
                            "🛒 Корзина",
                            callback_data="cart"
                        ),

                        types.InlineKeyboardButton(
                            "🛒 Корзина",
                            callback_data="cart"
                        ),
                        types.InlineKeyboardButton(
                            "◀️ К категориям",
                            callback_data="categories"
                        )


                    )

                    bot.send_message(chat_id, text, reply_markup=markup)

        elif call.data.startswith("add_"):
            _, category_id, product_id = call.data.split("_")
            products = asyncio.run(fetch_products_by_category(category_id))

            if not products:
                bot.answer_callback_query(call.id, "❌ Ошибка получения данных о товаре")
                return

            product = next((p for p in products if str(p['id']) == product_id), None)

            if product:
                db.add_to_cart(chat_id, int(product_id), product['name'], product['price'])

                quantity = db.get_item_quantity(chat_id, int(product_id))
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton(
                        "✅ Добавить в корзину",
                        callback_data=f"add_{category_id}_{product_id}"
                    ),
                    types.InlineKeyboardButton(
                        "❌ Убрать из корзины",
                        callback_data=f"remove_{category_id}_{product_id}"
                    ),
                    types.InlineKeyboardButton(
                        "🛒 Корзина",
                        callback_data="cart"
                    ),
                    types.InlineKeyboardButton(
                        "◀️ К категориям",
                        callback_data="categories"
                    )
                )

                try:
                    bot.edit_message_text(
                        f"📦 {product['name']}\n💰 Цена: {product['price']} ProCoin\n🛍 В корзине: {quantity} шт.",
                        chat_id,
                        message_id,
                        reply_markup=markup
                    )
                except telebot.apihelper.ApiException:
                    pass

                bot.answer_callback_query(
                    call.id,
                    f"✅ {product['name']} добавлен в корзину"
                )
            else:
                bot.answer_callback_query(call.id, "❌ Товар не найден")

        elif call.data.startswith("remove_"):
            _, category_id, product_id = call.data.split("_")
            products = asyncio.run(fetch_products_by_category(category_id))

            if not products:
                bot.answer_callback_query(call.id, "❌ Ошибка получения данных о товаре")
                return

            product = next((p for p in products if str(p['id']) == product_id), None)

            if product:
                if db.remove_from_cart(chat_id, int(product_id)):
                    quantity = db.get_item_quantity(chat_id, int(product_id))
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        types.InlineKeyboardButton(
                            "✅ Добавить в корзину",
                            callback_data=f"add_{category_id}_{product_id}"
                        ),
                        types.InlineKeyboardButton(
                            "❌ Убрать из корзины",
                            callback_data=f"remove_{category_id}_{product_id}"
                        ),

                    )

                    quantity_text = f"\n🛍 В корзине: {quantity} шт." if quantity > 0 else ""
                    try:
                        bot.edit_message_text(
                            f"📦 {product['name']}\n💰 Цена: {product['price']} ProCoin{quantity_text}",
                            chat_id,
                            message_id,
                            reply_markup=markup
                        )
                    except telebot.apihelper.ApiException:
                        pass

                    bot.answer_callback_query(
                        call.id,
                        f"✅ {product['name']} удален из корзины"
                    )
                else:
                    bot.answer_callback_query(call.id, "❌ Товар не найден в корзине")
            else:
                bot.answer_callback_query(call.id, "❌ Товар не найден")

        elif call.data == "cart":
            cart_items = db.get_cart(chat_id)
            if not cart_items:
                try:
                    bot.edit_message_text(
                        "🛒 Ваша корзина пуста",
                        chat_id,
                        message_id,
                        reply_markup=Keyboard.main_menu()
                    )
                except telebot.apihelper.ApiException:
                    bot.send_message(
                        chat_id,
                        "🛒 Ваша корзина пуста",
                        reply_markup=Keyboard.main_menu()
                    )
                return

            cart_text = "🛒 Ваша корзина:\n\n"
            total = 0
            for name, price, quantity in cart_items:
                item_total = price * quantity
                total += item_total
                cart_text += f"• {name}\n  {quantity} × {price} = {item_total} ProCoin\n"
            cart_text += f"\n💰 Итого: {total} ProCoin"

            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("💳 Оформить заказ", callback_data="checkout"),
                types.InlineKeyboardButton("♻ Очистить корзину", callback_data="clear_cart"),
                types.InlineKeyboardButton("◀️ Продолжить покупки", callback_data="categories")
            )

            try:
                bot.edit_message_text(
                    cart_text,
                    chat_id,
                    message_id,
                    reply_markup=markup
                )
            except telebot.apihelper.ApiException:
                bot.send_message(
                    chat_id,
                    cart_text,
                    reply_markup=markup
                )

        elif call.data == "clear_cart":
            db.clear_cart(chat_id)
            try:
                bot.edit_message_text(
                    "🗑 Корзина очищена!",
                    chat_id,
                    message_id,
                    reply_markup=Keyboard.main_menu()
                )
            except telebot.apihelper.ApiException:
                bot.send_message(
                    chat_id,
                    "🗑 Корзина очищена!",
                    reply_markup=Keyboard.main_menu()
                )

        elif call.data == "checkout":
            cart_items = db.get_cart(chat_id)
            if not cart_items:
                bot.answer_callback_query(call.id, "🛒 Ваша корзина пуста")
                return

            total = sum(item[1] * item[2] for item in cart_items)

            user_info = db.get_user(user_id)
            if not user_info:
                bot.answer_callback_query(call.id, "❌ Ошибка получения данных пользователя")
                return

            protaxi_id = user_info[1]

            # Проверяем баланс пользователя
            user_balance = asyncio.run(get_user_balance(protaxi_id))

            if total > user_balance:
                bot.answer_callback_query(call.id)
                bot.edit_message_text(
                    "❌ У вас недостаточно баллов для оформления заказа.\n"
                    "Попробуйте удалить из корзины некоторые товары и попробуйте снова.\n\n"
                    f"Сумма заказа: {total} ProCoin\n"
                    f"Ваш баланс: {user_balance} ProCoin",
                    chat_id,
                    message_id,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("◀️ Вернуться в корзину", callback_data="cart")
                    )
                )
                return

            if send_order_email(chat_id, cart_items, total):
                db.clear_cart(chat_id)
                try:
                    bot.edit_message_text(
                        "✅ Заказ успешно оформлен!\n"
                        "Мы свяжемся с вами в ближайшее время.",
                        chat_id,
                        message_id,
                        reply_markup=Keyboard.main_menu()
                    )
                except telebot.apihelper.ApiException:
                    bot.send_message(
                        chat_id,
                        "✅ Заказ успешно оформлен!\n"
                        "Мы свяжемся с вами в ближайшее время.",
                        reply_markup=Keyboard.main_menu()
                    )
            else:
                bot.edit_message_text(
                    "❌ Ошибка при оформлении заказа. Пожалуйста, попробуйте позже.",
                    chat_id,
                    message_id,
                    reply_markup=Keyboard.main_menu()
                )

    except Exception as e:
        logger.error(f"Callback handling error: {e}")
        try:
            bot.answer_callback_query(
                call.id,
                "❌ Произошла ошибка. Попробуйте еще раз."
            )
        except:
            pass

    def main():
        urls = [
            "https://protaxi-market.uz/module/shop/api/get-all-products"
        ]
        results = asyncio.run(fetch_all_products())

        for result in results:
            if result is not None:
                print(result)

if __name__ == "__main__":
    bot.polling(none_stop=True)