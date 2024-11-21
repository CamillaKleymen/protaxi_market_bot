import json
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
        balance = user_states[user_id]['balance']  # Баланс уже сохранен ранее
        language = user_states[user_id]['language']

        if asyncio.run(verify_login(protaxi_id, password)):
            if not db.get_user(user_id):
                db.add_user(user_id, protaxi_id, f"ProTaxi_{protaxi_id}")
                db.set_user_language(user_id, language)

            # Форматируем приветственное сообщение с балансом
            welcome_message = Languages.get_string(language, 'auth_success').format(balance)

            user_states[user_id] = {'language': language}

            bot.send_message(
                message.chat.id,
                welcome_message,
                reply_markup=types.ReplyKeyboardRemove()
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


def submit_order(user_id, cart_items, total):
    try:
        # Логируем начало процесса
        logger.info(f"Starting order submission for user {user_id}")
        logger.info(f"Total cart items: {len(cart_items)}")
        logger.info(f"Total order value: {total} ProCoin")

        # Проверяем, пустая ли корзина
        if not cart_items:
            logger.warning(f"Attempt to submit empty order for user {user_id}")
            return False

        # Получаем информацию о пользователе
        user_info = db.get_user(user_id)
        if not user_info:
            logger.error(f"Failed to find user info for user {user_id}")
            return False

        protaxi_id = user_info[1]
        logger.info(f"User ProTaxi ID: {protaxi_id}")

        # Подготавливаем данные для отправки
        products_data = [
            {
                'id': str(item[0]),
                'qty': str(item[2]),  # Количество
                'total': str(item[1] * item[2])  # Цена * количество
            } for item in cart_items
        ]

        # Логируем детали товаров в заказе
        for product in products_data:
            logger.info(
                f"Product in order - ID: {product['id']}, Quantity: {product['qty']}, Total: {product['total']}")

        data = {
            'user': protaxi_id,
            'products': products_data
        }

        # Логируем полные данные запроса
        logger.info(f"Full order data: {json.dumps(data, indent=2)}")

        # Отправляем POST-запрос
        headers = {
            'Content-type': 'application/json',
            'Accept': 'text/plain'
        }

        logger.info(f"Sending order to URL: {Config.SUBMIT_API_URL}")

        try:
            response = requests.post(Config.SUBMIT_API_URL, data=json.dumps(data), headers=headers)

            # Подробное логирование ответа
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response content: {response.text}")

            # Проверяем успешность отправки
            if response.status_code == 200:
                logger.info(f"Order submitted successfully for user {user_id}")
                return True
            else:
                logger.error(f"Failed to submit order. Status: {response.status_code}, Response: {response.text}")
                return False

        except requests.RequestException as req_error:
            logger.error(f"Network error during order submission: {req_error}")
            return False

    except Exception as e:
        logger.error(f"Unexpected error during order submission: {e}", exc_info=True)
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

        # Get user language, default to Russian
        user_language = db.get_user_language(user_id) or 'ru'

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
                    Languages.get_string(user_language, 'main_menu'),
                    chat_id,
                    message_id,
                    reply_markup=Keyboard.main_menu(user_language)
                )
            except telebot.apihelper.ApiException:
                bot.send_message(
                    chat_id,
                    Languages.get_string(user_language, 'main_menu'),
                    reply_markup=Keyboard.main_menu(user_language)
                )

        elif call.data == "categories":
            categories = fetch_all_categories()
            if not categories:
                bot.answer_callback_query(
                    call.id,
                    Languages.get_string(user_language, 'categories_unavailable')
                )
                return

            markup = types.InlineKeyboardMarkup(row_width=1)
            for category in categories:
                category_button = types.InlineKeyboardButton(
                    category['name'],
                    callback_data=f"show_products_{category['id']}"
                )
                markup.add(category_button)
            markup.add(
                types.InlineKeyboardButton(
                    Languages.get_string(user_language, 'back'),
                    callback_data="main_menu"
                )
            )

            try:
                bot.edit_message_text(
                    Languages.get_string(user_language, 'categories'),
                    chat_id,
                    message_id,
                    reply_markup=markup
                )
            except telebot.apihelper.ApiException:
                bot.send_message(
                    chat_id,
                    Languages.get_string(user_language, 'categories'),
                    reply_markup=markup
                )

        elif call.data.startswith("show_products_"):
            category_id = call.data.split("_")[2]
            products = asyncio.run(fetch_products_by_category(category_id))

            if not products:
                bot.edit_message_text(
                    Languages.get_string(user_language, 'no_products_in_category'),
                    chat_id,
                    message_id,
                    reply_markup=Keyboard.main_menu(user_language)
                )
                return

            bot.delete_message(chat_id, message_id)

            for product in products:
                try:
                    text = Languages.get_string(user_language, 'product_template').format(
                        product['name'],
                        product['price'],
                        product['currency']
                    )
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        types.InlineKeyboardButton(
                            Languages.get_string(user_language, 'add_to_cart'),
                            callback_data=f"add_{category_id}_{product['id']}"
                        ),
                        types.InlineKeyboardButton(
                            Languages.get_string(user_language, 'cart'),
                            callback_data="cart"
                        ),
                        types.InlineKeyboardButton(
                            Languages.get_string(user_language, 'to_categories'),
                            callback_data="categories"
                        )
                    )

                    if 'image' in product and product['image']:
                        bot.send_photo(
                            chat_id,
                            photo=product['image'],
                            caption=text,
                            reply_markup=markup
                        )
                    else:
                        bot.send_message(chat_id, text, reply_markup=markup)

                except Exception as e:
                    logger.error(f"Error sending product: {e}")

        elif call.data.startswith("add_"):
            _, category_id, product_id = call.data.split("_")
            products = asyncio.run(fetch_products_by_category(category_id))

            if not products:
                bot.answer_callback_query(
                    call.id,
                    Languages.get_string(user_language, 'product_not_found')
                )
                return

            product = next((p for p in products if str(p['id']) == product_id), None)

            if product:
                db.add_to_cart(chat_id, int(product_id), product['name'], product['price'])

                quantity = db.get_item_quantity(chat_id, int(product_id))
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton(
                        Languages.get_string(user_language, 'add_to_cart'),
                        callback_data=f"add_{category_id}_{product_id}"
                    ),
                    types.InlineKeyboardButton(
                        Languages.get_string(user_language, 'remove_from_cart'),
                        callback_data=f"remove_{category_id}_{product_id}"
                    ),
                    types.InlineKeyboardButton(
                        Languages.get_string(user_language, 'cart'),
                        callback_data="cart"
                    ),
                    types.InlineKeyboardButton(
                        Languages.get_string(user_language, 'to_categories'),
                        callback_data="categories"
                    )
                )

                try:
                    bot.edit_message_text(
                        Languages.get_string(user_language, 'product_template').format(
                            product['name'], product['price'], product['currency']
                        ) + Languages.get_string(user_language, 'in_cart').format(quantity),
                        chat_id,
                        message_id,
                        reply_markup=markup
                    )
                except telebot.apihelper.ApiException:
                    pass

                bot.answer_callback_query(
                    call.id,
                    Languages.get_string(user_language, 'product_added').format(product['name'])
                )
            else:
                bot.answer_callback_query(
                    call.id,
                    Languages.get_string(user_language, 'product_not_found')
                )

        elif call.data.startswith("remove_"):
            _, category_id, product_id = call.data.split("_")
            products = asyncio.run(fetch_products_by_category(category_id))

            if not products:
                bot.answer_callback_query(
                    call.id,
                    Languages.get_string(user_language, 'product_not_found')
                )
                return

            product = next((p for p in products if str(p['id']) == product_id), None)

            if product:
                if db.remove_from_cart(chat_id, int(product_id)):
                    quantity = db.get_item_quantity(chat_id, int(product_id))
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        types.InlineKeyboardButton(
                            Languages.get_string(user_language, 'add_to_cart'),
                            callback_data=f"add_{category_id}_{product_id}"
                        ),
                        types.InlineKeyboardButton(
                            Languages.get_string(user_language, 'remove_from_cart'),
                            callback_data=f"remove_{category_id}_{product_id}"
                        ),
                        types.InlineKeyboardButton(
                            Languages.get_string(user_language, 'cart'),
                            callback_data="cart"
                        ),
                        types.InlineKeyboardButton(
                            Languages.get_string(user_language, 'to_categories'),
                            callback_data="categories"
                        )
                    )

                    quantity_text = Languages.get_string(user_language, 'in_cart').format(quantity) if quantity > 0 else ""
                    try:
                        bot.edit_message_text(
                            Languages.get_string(user_language, 'product_template').format(
                                product['name'], product['price'], product['currency']
                            ) + quantity_text,
                            chat_id,
                            message_id,
                            reply_markup=markup
                        )
                    except telebot.apihelper.ApiException:
                        pass

                    bot.answer_callback_query(
                        call.id,
                        Languages.get_string(user_language, 'product_removed').format(product['name'])
                    )
                else:
                    bot.answer_callback_query(
                        call.id,
                        Languages.get_string(user_language, 'product_not_in_cart')
                    )
            else:
                bot.answer_callback_query(
                    call.id,
                    Languages.get_string(user_language, 'product_not_found')
                )

        elif call.data == "cart":
            cart_items = db.get_cart(chat_id)
            if not cart_items:
                try:
                    bot.edit_message_text(
                        Languages.get_string(user_language, 'cart_empty'),
                        chat_id,
                        message_id,
                        reply_markup=Keyboard.main_menu(user_language)
                    )
                except telebot.apihelper.ApiException:
                    bot.send_message(
                        chat_id,
                        Languages.get_string(user_language, 'cart_empty'),
                        reply_markup=Keyboard.main_menu(user_language)
                    )
                return

            cart_text = Languages.get_string(user_language, 'cart_header') + "\n\n"
            total = 0
            for name, price, quantity in cart_items:
                item_total = price * quantity
                total += item_total
                cart_text += Languages.get_string(user_language, 'cart_item').format(
                    name, quantity, price, item_total
                )
            cart_text += Languages.get_string(user_language, 'cart_total').format(total)

            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton(
                    Languages.get_string(user_language, 'checkout'),
                    callback_data="checkout"
                ),
                types.InlineKeyboardButton(
                    Languages.get_string(user_language, 'clear_cart'),
                    callback_data="clear_cart"
                ),
                types.InlineKeyboardButton(
                    Languages.get_string(user_language, 'continue_shopping'),
                    callback_data="categories"
                )
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
                    Languages.get_string(user_language, 'cart_cleared'),
                    chat_id,
                    message_id,
                    reply_markup=Keyboard.main_menu(user_language)
                )
            except telebot.apihelper.ApiException:
                bot.send_message(
                    chat_id,
                    Languages.get_string(user_language, 'cart_cleared'),
                    reply_markup=Keyboard.main_menu(user_language)
                )

        elif call.data == "checkout":
            cart_items = db.get_cart(chat_id)
            if not cart_items:
                bot.answer_callback_query(
                    call.id,
                    Languages.get_string(user_language, 'cart_empty')
                )
                return

            total = sum(item[1] * item[2] for item in cart_items)

            user_info = db.get_user(user_id)
            if not user_info:
                bot.answer_callback_query(
                    call.id,
                    Languages.get_string(user_language, 'user_data_error')
                )
                return

            protaxi_id = user_info[1]
            user_balance = asyncio.run(get_user_balance(protaxi_id))

            if total > user_balance:
                bot.answer_callback_query(call.id)
                bot.edit_message_text(
                    Languages.get_string(user_language, 'insufficient_balance').format(
                        total, user_balance
                    ),
                    chat_id,
                    message_id,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton(
                            Languages.get_string(user_language, 'back_to_cart'),
                            callback_data="cart"
                        )
                    )
                )
                return

            if submit_order(chat_id, cart_items, total):
                db.clear_cart(chat_id)
                try:
                    bot.edit_message_text(
                        Languages.get_string(user_language, 'order_success'),
                        chat_id,
                        message_id,
                        reply_markup=Keyboard.main_menu(user_language)
                    )
                except telebot.apihelper.ApiException:
                    bot.send_message(
                        chat_id,
                        Languages.get_string(user_language, 'order_success'),
                        reply_markup=Keyboard.main_menu(user_language)
                    )
            else:
                bot.edit_message_text(
                    Languages.get_string(user_language, 'order_error'),
                    chat_id,
                    message_id,
                    reply_markup=Keyboard.main_menu(user_language)
                )

    except Exception as e:
        logger.error(f"Callback handling error: {e}")
        try:
            bot.answer_callback_query(
                call.id,
                Languages.get_string(user_language, 'error')
            )
        except:
            pass

if __name__ == "__main__":
    bot.polling(none_stop=True)