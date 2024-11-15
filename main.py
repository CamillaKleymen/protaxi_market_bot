import logging
import smtplib
import sqlite3
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from database import db
from buttons import Keyboard

import aiohttp
import asyncio
import requests
import telebot
from telebot import types

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
API_TOKEN = '7534486887:AAFclAId55bLPlE6QoYWwGzX1nMX-j6pfJs'
bot = telebot.TeleBot(API_TOKEN)

# Email конфигурация
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = "camillakleymen@gmail.com"
EMAIL_HOST_PASSWORD = "zqrz tgqi zgpt yvyp"
EMAIL_RECIPIENT = "camillakleymen@gmail.com"

# API URLs
BASE_API_URL = "https://protaxi-market.uz/module/shop/api"
CHECK_ID_URL = f"{BASE_API_URL}/check-id"
LOGIN_URL = f"{BASE_API_URL}/login"
CATEGORIES_API_URL = f"{BASE_API_URL}/get-all-categories"
PRODUCTS_API_URL = f"{BASE_API_URL}/get-all-products"

# Состояния пользователей
user_states = {}


# Функции проверки API
async def check_protaxi_id(protaxi_id):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CHECK_ID_URL}?id={protaxi_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('success') is True
                return False
    except Exception as e:
        logger.error(f"Error checking ProTaxi ID: {e}")
        return False


async def verify_login(protaxi_id, password):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{LOGIN_URL}?id={protaxi_id}&password={password}") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('success') is True
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
            bot.send_message(
                message.chat.id,
                "👋 Добро пожаловать! Введите пожалуйста Ваш ProTaxi ID:"
            )
            user_states[user_id] = {'state': 'waiting_for_id'}
            bot.register_next_step_handler(message, process_protaxi_id)
        else:
            show_main_menu(message.chat.id)
    except Exception as e:
        logger.error(f"Start error: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте позже.")


def process_protaxi_id(message):
    try:
        user_id = message.from_user.id
        protaxi_id = message.text.strip()

        if asyncio.run(check_protaxi_id(protaxi_id)):
            user_states[user_id] = {
                'state': 'waiting_for_password',
                'protaxi_id': protaxi_id
            }
            bot.send_message(
                message.chat.id,
                "✅ ID подтвержден. Пожалуйста, введите ваш пароль:"
            )
            bot.register_next_step_handler(message, process_password)
        else:
            bot.send_message(
                message.chat.id,
                "❌ Такого ProTaxi ID не существует. Пожалуйста, проверьте и введите корректный ID:"
            )
            bot.register_next_step_handler(message, process_protaxi_id)
    except Exception as e:
        logger.error(f"Process ProTaxi ID error: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте /start снова.")


def process_password(message):
    try:
        user_id = message.from_user.id
        if user_id not in user_states:
            bot.send_message(message.chat.id, "❌ Ошибка сессии. Пожалуйста, начните сначала с команды /start")
            return

        password = message.text.strip()
        protaxi_id = user_states[user_id]['protaxi_id']

        if asyncio.run(verify_login(protaxi_id, password)):
            if not db.get_user(user_id):
                db.add_user(user_id, protaxi_id, f"ProTaxi_{protaxi_id}")

            del user_states[user_id]

            bot.send_message(
                message.chat.id,
                "✅ Авторизация успешна!\n\n"
                "🛍 Добро пожаловать в наш магазин!\n"
                "Выберите раздел из меню ниже:"
            )
            show_main_menu(message.chat.id)
        else:
            bot.send_message(
                message.chat.id,
                "❌ Неверный пароль. Пожалуйста, попробуйте еще раз:"
            )
            bot.register_next_step_handler(message, process_password)
    except Exception as e:
        logger.error(f"Process password error: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте /start снова.")


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
    data = await fetch_product_data(PRODUCTS_API_URL)
    return data


def fetch_all_categories():
    try:
        response = requests.get(CATEGORIES_API_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch categories: {e}")
        return []


async def fetch_products_by_category(category_id):
    url = f"{PRODUCTS_API_URL}?category_id={category_id}"
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
    # Форматирование каждого элемента корзины
    for name, price, quantity in cart_items:
        item_total = price * quantity
        message_text += f"{name.ljust(25)} {str(quantity).rjust(3)} шт. × {str(price).rjust(8)} ProCoin = {str(item_total).rjust(8)} ProCoin\n"

    # Итоговая сумма заказа
    message_text += f"\n-------------------------\nИтоговая сумма заказа: {str(total).rjust(8)} ProCoin"

    return message_text


def send_order_email(user_id, cart_items, total):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_HOST_USER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = f'Новый заказ #{user_id} от {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

        message_text = format_order_email(user_id, cart_items, total)
        if not message_text:
            logger.error(f"Failed to format email for user {user_id}")
            return False

        msg.attach(MIMEText(message_text, 'plain'))

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.send_message(msg)

        logger.info(f"Order email sent successfully for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send order email: {e}")
        return False


# Вспомогательные функции
def show_main_menu(chat_id):
    try:
        bot.send_message(
            chat_id,
            "📋 Главное меню:",
            reply_markup=Keyboard.main_menu()
        )
    except Exception as e:
        logger.error(f"Show main menu error: {e}")
        bot.send_message(chat_id, "❌ Произошла ошибка. Попробуйте позже.")


# Обработчик callback-запросов
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        chat_id = call.message.chat.id
        message_id = call.message.message_id

        if call.data == "main_menu":
            bot.edit_message_text(
                "📋 Главное меню:",
                chat_id,
                message_id,
                reply_markup=Keyboard.main_menu()
            )

        elif call.data == "categories":
            categories = fetch_all_categories()
            if not categories:
                bot.edit_message_text(
                    "😔 К сожалению, категории временно недоступны.",
                    chat_id,
                    message_id,
                    reply_markup=Keyboard.main_menu()
                )
                return

            markup = types.InlineKeyboardMarkup(row_width=1)
            for category in categories:
                category_button = types.InlineKeyboardButton(
                    category['name'],
                    callback_data=f"show_products_{category['id']}"
                )
                markup.add(category_button)
            markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))

            bot.edit_message_text(
                "📂 Выберите категорию:",
                chat_id,
                message_id,
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
                bot.answer_callback_query(
                    call.id,
                    f"✅ {product['name']} добавлен в корзину"
                )
            else:
                bot.answer_callback_query(call.id, "❌ Товар не найден")

        elif call.data == "cart":
            cart_items = db.get_cart(chat_id)
            if not cart_items:
                bot.edit_message_text(
                    "🛒 Ваша корзина пуста",
                    chat_id,
                    message_id,
                    reply_markup=Keyboard.main_menu()
                )
                return

            cart_text = "🛒 Ваша корзина:\n\n"
            total = 0
            for name, price, quantity in cart_items:
                item_total = price * quantity
                total += item_total
                cart_text += f"• {name} - {quantity} x {price} = {item_total}ProCoin\n"
            cart_text += f"\n💰 Итого: {total}ProCoin"

            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("💳 Оформить заказ", callback_data="checkout"),
                types.InlineKeyboardButton("🗑 Очистить корзину", callback_data="clear_cart"),
                types.InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
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
            bot.edit_message_text(
                "🗑 Корзина очищена!",
                chat_id,
                message_id,
                reply_markup=Keyboard.main_menu()
            )

        elif call.data == "checkout":
            cart_items = db.get_cart(chat_id)
            if not cart_items:
                bot.edit_message_text(
                    "🛒 Ваша корзина пуста.",
                    chat_id,
                    message_id,
                    reply_markup=Keyboard.main_menu()
                )
                return

            total = sum(item[1] * item[2] for item in cart_items)
            if send_order_email(chat_id, cart_items, total):
                db.clear_cart(chat_id)
                bot.edit_message_text(
                    "✅ Заказ успешно оформлен! Мы свяжемся с вами в ближайшее время.",
                    chat_id,
                    message_id,
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
        bot.send_message(chat_id, "❌ Произошла ошибка. Попробуйте позже.")

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