import telebot


class Config:
    # TELEGRAM bot TOKEN
    API_TOKEN = '7534486887:AAFclAId55bLPlE6QoYWwGzX1nMX-j6pfJs'
    # bot = telebot.TeleBot(API_TOKEN)


    # EMAIL API/HOST
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_HOST_USER = "camillakleymen@gmail.com"
    EMAIL_HOST_PASSWORD = "zqrz tgqi zgpt yvyp"
    EMAIL_RECIPIENT = "camillakleymen@gmail.com"

    # MAIN API URLs
    BASE_API_URL = "https://protaxi-market.uz/module/shop/api"
    CHECK_ID_URL = f"{BASE_API_URL}/check-id"
    LOGIN_URL = f"{BASE_API_URL}/login"
    CATEGORIES_API_URL = f"{BASE_API_URL}/get-all-categories"
    PRODUCTS_API_URL = f"{BASE_API_URL}/get-all-products"
    SUBMIT_API_URL = f"{BASE_API_URL}/submit"


    # # Конфигурация
    # API_TOKEN = '7534486887:AAFclAId55bLPlE6QoYWwGzX1nMX-j6pfJs'
    # bot = telebot.TeleBot(API_TOKEN)
    #
    # # Email конфигурация
    # EMAIL_HOST = 'smtp.gmail.com'
    # EMAIL_PORT = 587
    # EMAIL_HOST_USER = "camillakleymen@gmail.com"
    # EMAIL_HOST_PASSWORD = "zqrz tgqi zgpt yvyp"
    # EMAIL_RECIPIENT = "camillakleymen@gmail.com"
    #
    # # API URLs
    # BASE_API_URL = "https://protaxi-market.uz/module/shop/api"
    # CHECK_ID_URL = f"{BASE_API_URL}/check-id"
    # LOGIN_URL = f"{BASE_API_URL}/login"
    # CATEGORIES_API_URL = f"{BASE_API_URL}/get-all-categories"
    # PRODUCTS_API_URL = f"{BASE_API_URL}/get-all-products"
