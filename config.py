import telebot


class Config:
    # TELEGRAM bot TOKEN
    API_TOKEN = '7534486887:AAFclAId55bLPlE6QoYWwGzX1nMX-j6pfJs'
    # bot = telebot.TeleBot(API_TOKEN)

    # MAIN API URLs
    BASE_API_URL = "https://protaxi-market.uz/module/shop/api"
    CHECK_ID_URL = f"{BASE_API_URL}/check-id"
    LOGIN_URL = f"{BASE_API_URL}/login"
    CATEGORIES_API_URL = f"{BASE_API_URL}/get-all-categories"
    PRODUCTS_API_URL = f"{BASE_API_URL}/get-all-products"
    SUBMIT_API_URL = f"{BASE_API_URL}/submit"


