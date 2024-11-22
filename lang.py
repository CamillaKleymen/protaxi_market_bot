# languages.py

class Languages:
    STRINGS = {
        'ru': {
            # Общие фразы
            'welcome': "👋 Добро пожаловать! Введите пожалуйста Ваш ProTaxi ID:",
            'error': "❌ Произошла ошибка. Попробуйте позже.",
            'restart': "❌ Произошла ошибка. Попробуйте /start снова.",
            'session_error': "❌ Ошибка сессии. Пожалуйста, начните сначала с команды /start",

            # Меню и навигация
            'main_menu': "📋 Главное меню:",
            'catalog': "🛍 Каталог",
            'cart': "🛒 Корзина",
            'back': "◀️ Назад",
            'categories': "📂 Выберите категорию:",
            'to_categories': "◀️ К категориям",
            'continue_shopping': "◀️ Продолжить покупки",

            # Авторизация
            'id_confirmed': "✅ ID подтвержден. Пожалуйста, введите ваш пароль:",
            'invalid_id': "❌ Такого ProTaxi ID не существует. Пожалуйста, проверьте и введите корректный ID:",
            'invalid_password': "❌ Неверный пароль. Пожалуйста, попробуйте еще раз:",
            'auth_success': "✅ Авторизация успешна!\n\n🛍 Добро пожаловать в наш магазин!\nВыберите раздел из меню ниже:",

            # Корзина
            'cart_empty': "🛒 Ваша корзина пуста",
            'cart_title': "🛒 Ваша корзина:\n\n",
            'cart_total': "\n💰 Итого: {} ProCoin",
            'cart_cleared': "🗑 Корзина очищена!",
            'checkout': "💳 Оформить заказ",
            'clear_cart': "♻ Очистить корзину",

            # Товары
            'add_to_cart': "✅ Добавить в корзину",
            'remove_from_cart': "❌ Убрать из корзины",
            'product_added': "✅ {} добавлен в корзину",
            'product_removed': "✅ {} удален из корзины",
            'product_not_found': "❌ Товар не найден",
            'product_template': "📦 {}\n💰 Цена: {} {}\n",
            'in_cart': "🛍 В корзине: {} шт.",

            # Оформление заказа
            'insufficient_balance': "❌ У вас недостаточно баллов для оформления заказа.\nПопробуйте удалить из корзины некоторые товары и попробуйте снова.\n\nСумма заказа: {} ProCoin\nВаш баланс: {} ProCoin",
            'order_success': "✅ Спасибо! Ваш Заказ успешно оформлен! ",
            'order_error': "❌ Ошибка при оформлении заказа. Пожалуйста, попробуйте позже.",

            # Категории
            'categories_unavailable': "😔 Категории временно недоступны",
            'no_products_in_category': "😔 К сожалению, товары в данной категории временно недоступны.",

            'cart_header': "🛒 Содержимое корзины:",
            'cart_item': "📦 {}: {} шт. × {} ProCoin = {} ProCoin\n",
            'back_to_cart': "◀️ Вернуться в корзину",
            'user_data_error': "❌ Ошибка получения данных пользователя",
            'product_not_in_cart': "❌ Товар не находится в корзине",

            'auth_success': "✅ Авторизация успешна!\n\n🛍 Добро пожаловать в наш магазин!\n💰 Ваш баланс: {} ProCoin\n\nВыберите раздел из меню ниже:",

        },

        'uz': {
            # Общие фразы
            'welcome': "👋 Xush kelibsiz! Iltimos, ProTaxi ID raqamingizni kiriting:",
            'error': "❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.",
            'restart': "❌ Xatolik yuz berdi. /start buyrug'ini qaytadan bosing.",
            'session_error': "❌ Sessiya xatosi. Iltimos, /start buyrug'i bilan qaytadan boshlang",

            # Меню и навигация
            'main_menu': "📋 Asosiy menyu:",
            'catalog': "🛍 Katalog",
            'cart': "🛒 Savatcha",
            'back': "◀️ Orqaga",
            'categories': "📂 Kategoriyani tanlang:",
            'to_categories': "◀️ Kategoriyalarga",
            'continue_shopping': "◀️ Xaridni davom ettirish",

            # Авторизация
            'id_confirmed': "✅ ID tasdiqlandi. Iltimos, parolingizni kiriting:",
            'invalid_id': "❌ Bunday ProTaxi ID mavjud emas. Iltimos, to'g'ri ID ni tekshirib, qayta kiriting:",
            'invalid_password': "❌ Noto'g'ri parol. Iltimos, qayta urinib ko'ring:",
            'auth_success': "✅ Avtorizatsiya muvaffaqiyatli!\n\n🛍 Bizning do'konimizga xush kelibsiz!\nQuyidagi menyudan bo'limni tanlang:",

            # Корзина
            'cart_empty': "🛒 Sizning savatingiz bo'sh",
            'cart_title': "🛒 Sizning savatingiz:\n\n",
            'cart_total': "\n💰 Jami: {} ProCoin",
            'cart_cleared': "🗑 Savatcha tozalandi!",
            'checkout': "💳 Buyurtma berish",
            'clear_cart': "♻ Savatchani tozalash",

            # Товары
            'add_to_cart': "✅ Savatchaga qo'shish",
            'remove_from_cart': "❌ Savatchadan olib tashlash",
            'product_added': "✅ {} savatchaga qo'shildi",
            'product_removed': "✅ {} savatchadan olib tashlandi",
            'product_not_found': "❌ Mahsulot topilmadi",
            'product_template': "📦 {}\n💰 Narxi: {} {}\n",
            'in_cart': "🛍 Savatchada: {} dona",

            # Оформление заказа
            'insufficient_balance': "❌ Buyurtma berish uchun ballingiz yetarli emas.\nSavatchadan ba'zi mahsulotlarni olib tashlab, qayta urinib ko'ring.\n\nBuyurtma summasi: {} ProCoin\nSizning balansingiz: {} ProCoin",
            'order_success': "✅ Buyurtma muvaffaqiyatli rasmiylashtirildi!",
            'order_error': "❌ Buyurtmani rasmiylashtirishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.",

            # Категории
            'categories_unavailable': "😔 Kategoriyalar vaqtincha mavjud emas",
            'no_products_in_category': "😔 Afsuski, ushbu kategoriyada mahsulotlar vaqtincha mavjud emas.",

            'cart_header': "🛒 Savatcha tarkibi:",
            'cart_item': "📦 {}: {} dona × {} ProCoin = {} ProCoin\n",
            'back_to_cart': "◀️ Savatchaga qaytish",
            'user_data_error': "❌ Foydalanuvchi ma'lumotlarini olishda xatolik",
            'product_not_in_cart': "❌ Mahsulot savatchada yo'q",

            'auth_success': "✅ Avtorizatsiya muvaffaqiyatli!\n\n🛍 Bizning do'konimizga xush kelibsiz!\n💰 Sizning balansingiz: {} ProCoin\n\nQuyidagi menyudan bo'limni tanlang:",


        }
    }

    @staticmethod
    def get_string(language: str, key: str) -> str:
        """
        Получить строку на нужном языке
        :param language: Код языка ('ru' или 'uz')
        :param key: Ключ строки
        :return: Строка на выбранном языке
        """
        return Languages.STRINGS.get(language, Languages.STRINGS['ru']).get(key, Languages.STRINGS['ru'][key])