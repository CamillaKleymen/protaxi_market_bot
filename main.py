import json
import logging
import aiohttp
import asyncio
import requests
import telebot


from database import db
from buttons import Keyboard
from lang import Languages
from config import Config
from telebot import types

"""log settings"""
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

"""global variable => bot token from config file"""
bot = telebot.TeleBot(Config.API_TOKEN)

"""user states"""
user_states = {}


"""function of choosing language"""
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

"""save in db choice of user lang."""
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


"""functions of checking user id"""
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

"""checiking user through API"""
async def verify_login(protaxi_id, password):
    """checking user through API"""
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



"""start of bot and process registration"""
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
        bot.register_next_step_handler(message, lambda m: asyncio.run(process_protaxi_id(m)))
    except Exception as e:
        logger.error(f"Set user language error: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте позже.")

async def process_protaxi_id(message):
    try:
        user_id = message.from_user.id
        protaxi_id = message.text.strip()
        language = user_states[user_id]['language']

        result = await check_protaxi_id(protaxi_id)
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
            bot.register_next_step_handler(message, lambda m: asyncio.run(process_protaxi_id(m)))
    except Exception as e:
        logger.error(f"Process ProTaxi ID error: {e}")
        bot.send_message(message.chat.id, Languages.get_string('ru', 'restart'))


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
                db.set_user_language(user_id, language)

            """message for display of user balance"""
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


"""API func actions"""
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


"""function for processing order *with logging"""
async def submit_order(user_id, cart_items, total):
    try:
        user_info = db.get_user(user_id)
        if not user_info:
            logger.error(f"Failed to find user info for user {user_id}")
            return False

        protaxi_id = user_info[1]
        products_data = [{
            'id': str(item[0]),
            'name': str(item[1]),
            'price': str(item[2]),
            'qty': str(item[3]),
            'total': str(float(item[2]) * item[3])
        } for item in cart_items]

        order_data = {
            'user': protaxi_id,
            'products': products_data,
            'total_amount': str(total)
        }


        logger.info(f"User ID (Telegram): {user_id}")
        logger.info(f"ProTaxi ID: {protaxi_id}")
        logger.info("Products in order:")
        for product in products_data:
            logger.info(f"""
    - Product ID: {product['id']}
    - Name: {product['name']}
    - Price: {product['price']}
    - Quantity: {product['qty']}
    - Subtotal: {product['total']}
            """)
        logger.info(f"Total Order Amount: {total}")
        logger.info("Raw JSON data being sent:")
        logger.info(json.dumps(order_data, indent=2, ensure_ascii=False))

        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    Config.SUBMIT_API_URL,
                    data=json.dumps(order_data),
                    headers=headers
            ) as response:
                response_text = await response.text()
                logger.info("order response")
                logger.info(f"Response Status Code: {response.status}")
                logger.info(f"Response Body: {response_text}")

                if response.status == 200:
                    try:
                        data = await response.json()
                        success = data.get('success', False)
                        logger.info(f"Order {'successful' if success else 'failed'} for user {user_id}")
                        return success
                    except Exception as json_error:
                        logger.error(f"JSON decoding error: {json_error}")
                        return False
                else:
                    logger.error(f"Unexpected status code: {response.status}")
                    return False

    except Exception as e:
        logger.error(f"Unexpected error during order submission: {e}")
        return False


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


"""processing of callback queries"""
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        user_id = call.from_user.id

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

            for product_id, name, price, quantity in cart_items:  # Исправлена распаковка
                item_total = float(price) * int(quantity)
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
            logger.info(f"Starting checkout process for user {user_id} in chat {chat_id}")
            cart_items = db.get_cart(chat_id)

            if not cart_items:
                logger.warning(f"Attempted checkout with empty cart - user {user_id}")
                bot.answer_callback_query(call.id, Languages.get_string(user_language, 'cart_empty'))
                return

            logger.info(f"Cart contents for user {user_id}:")
            total = 0

            for item in cart_items:
                item_total = float(item[2]) * int(item[3])
                total += item_total
                logger.info(f"- Product: {item[1]}, Quantity: {item[3]}, Price: {item[2]}, Subtotal: {item_total}")

            logger.info(f"Total order amount: {total}")

            user_info = db.get_user(user_id)

            if not user_info:
                logger.error(f"User data error during checkout - user {user_id}")
                bot.answer_callback_query(call.id, Languages.get_string(user_language, 'user_data_error'))
                return

            protaxi_id = user_info[1]
            logger.info(f"Checking balance for ProTaxi ID: {protaxi_id}")
            user_balance = asyncio.run(get_user_balance(protaxi_id))
            logger.info(f"User balance: {user_balance}, Required amount: {total}")

            if total > user_balance:
                logger.warning(f"Insufficient funds - user {user_id}, balance: {user_balance}, total: {total}")
                bot.edit_message_text(
                    Languages.get_string(user_language, 'insufficient_balance').format(total, user_balance),
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

            logger.info(f"Submitting order for user {user_id} with total amount {total}")
            order_result = asyncio.run(submit_order(user_id, cart_items, total))
            logger.info(f"Order submission result for user {user_id}: {order_result}")

            try:
                if order_result:
                    logger.info(f"Order successful for user {user_id}. Clearing cart.")
                    db.clear_cart(chat_id)
                    bot.edit_message_text(
                        Languages.get_string(user_language, 'order_success'),
                        chat_id,
                        message_id,
                        reply_markup=Keyboard.main_menu(user_language)
                    )
                    logger.info(f"Checkout completed successfully for user {user_id}")
                else:
                    logger.error(f"Order submission failed for user {user_id}")
                    bot.edit_message_text(
                        Languages.get_string(user_language, 'order_error'),
                        chat_id,
                        message_id,
                        reply_markup=Keyboard.main_menu(user_language)
                    )


            except telebot.apihelper.ApiException as api_error:
                logger.error(f"Telegram API error during message edit: {api_error}")

                if order_result:
                    logger.info(f"Sending new success message for user {user_id}")
                    bot.send_message(
                        chat_id,
                        Languages.get_string(user_language, 'order_success'),
                        reply_markup=Keyboard.main_menu(user_language)
                    )

                else:
                    logger.error(f"Sending new error message for user {user_id}")
                    bot.send_message(
                        chat_id,
                        Languages.get_string(user_language, 'order_error'),
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