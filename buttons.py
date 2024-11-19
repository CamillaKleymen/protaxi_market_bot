from telebot import types

from lang import Languages


# настройка клавиатуры и  работа кнопок
class Keyboard:
    @staticmethod
    def get_phone_number():
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button = types.KeyboardButton("📞 Отправить номер телефона", request_contact=True)
        markup.add(button)
        return markup

    @staticmethod
    def main_menu():
        markup = types.InlineKeyboardMarkup(row_width=2)
        catalog = types.InlineKeyboardButton("🛍 Каталог", callback_data="categories")
        cart = types.InlineKeyboardButton("🛒 Корзина", callback_data="cart")
        # support = types.InlineKeyboardButton("💬 Поддержка/Отзыв", callback_data="support")
        # feedback = types.InlineKeyboardButton("📝 Отзыв", callback_data="feedback")
        markup.add(catalog, cart)
        return markup

    @staticmethod
    def product_markup(product_id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        add_to_cart = types.InlineKeyboardButton("✅ Добавить в корзину",
                                                 callback_data=f"add_{product_id}")
        cart = types.InlineKeyboardButton("🛒 Корзина", callback_data="cart")
        back = types.InlineKeyboardButton("◀️ Назад", callback_data="categories")
        markup.add(add_to_cart, cart, back)
        return markup

    @staticmethod
    def cart_markup():
        markup = types.InlineKeyboardMarkup(row_width=2)
        checkout = types.InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")
        clear = types.InlineKeyboardButton("🗑 Очистить корзину", callback_data="clear_cart")
        back = types.InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
        markup.add(checkout, clear, back)
        return markup

