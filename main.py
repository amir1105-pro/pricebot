import telebot
import requests
import sqlite3
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, Message
import logging

# -------- تنظیمات اصلی --------
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
BOT_TOKEN = "your token"
ADMINS = [332034345]

bot = telebot.TeleBot(BOT_TOKEN)

# -------- دیتابیس --------
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    joined_at TEXT
)
''')
conn.commit()

# -------- کلاس‌های کاربر و ادمین --------
class User:
    def __init__(self, user_obj):
        self.id = user_obj.id
        self.username = user_obj.username or "-"
        self.first_name = user_obj.first_name or "-"
        self.is_admin = self.id in ADMINS

    def save(self):
        joined_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at)
            VALUES (?, ?, ?, ?)
        """, (self.id, self.username, self.first_name, joined_time))
        conn.commit()

        try:
            with open("users.txt", "a", encoding="utf-8") as file:
                file.write(f"{self.id},{self.username},{self.first_name},{joined_time}\n")
        except Exception as e:
            logging.error(f"خطا در ذخیره در فایل: {e}")

    def get_menu(self):
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            KeyboardButton("🚀 ارز های انفجاری امروز"),
            KeyboardButton("📊 دریافت قیمت با نماد")
        )
        return markup

class Admin(User):
    def get_menu(self):
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            KeyboardButton("📢 ارسال پیام همگانی"),
            KeyboardButton("👥 تعداد کاربران"),
            KeyboardButton("🚀 ارز های انفجاری امروز"),
            KeyboardButton("📊 دریافت قیمت با نماد"),
            KeyboardButton("❌ خروج از حالت ادمین")
        )
        return markup

# -------- کش و وضعیت‌ها --------
cached_top_coins = None
last_cache_time = None
CACHE_DURATION = timedelta(minutes=65)
broadcast_state = {}

# -------- توابع کمکی --------
def get_usdt_price_irr():
    try:
        url = "https://api.nobitex.ir/market/stats"
        data = {"srcCurrency": "usdt", "dstCurrency": "rls"}
        response = requests.post(url, data=data)
        response.raise_for_status()
        result = response.json()
        return float(result["stats"]["usdt-rls"]["latest"])
    except Exception as e:
        logging.error(f"خطا در دریافت قیمت USDT از نوبیتکس: {e}")
        return 800000

def count_users():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]

# -------- هندلر /start --------
@bot.message_handler(commands=['start'])
def start_handler(message: Message):
    user = Admin(message.from_user) if message.from_user.id in ADMINS else User(message.from_user)
    user.save()
    greeting = (
        "🎉 *به ربات قیمت ارز دیجیتال خوش آمدید!*\n\nلطفا از منو یکی از گزینه‌ها را انتخاب کنید. 👇"
        if not user.is_admin else
        "👑 *خوش آمدید ادمین عزیز!*\n\nاز منوی زیر گزینه‌ای را انتخاب کنید. ⚙️"
    )
    bot.send_message(message.chat.id, greeting, reply_markup=user.get_menu(), parse_mode="Markdown")

# -------- ارزهای با بیشترین رشد --------
@bot.message_handler(func=lambda m: m.text == "🚀 ارز های انفجاری امروز")
def show_top_gainers(message: Message):
    global cached_top_coins, last_cache_time
    now = datetime.now()

    if not cached_top_coins or not last_cache_time or now - last_cache_time > CACHE_DURATION:
        bot.send_message(message.chat.id, "⏳ در حال دریافت اطلاعات ۲۵۰ ارز برتر از CoinGecko...")
        try:
            coins = []
            for page in range(1, 3):  # دو صفحه 125تایی = 250 ارز برتر
                url = "https://api.coingecko.com/api/v3/coins/markets"
                params = {
                    'vs_currency': 'usd',
                    'order': 'market_cap_desc',
                    'per_page': 125,
                    'page': page,
                    'price_change_percentage': '24h'
                }
                resp = requests.get(url, params=params)
                coins.extend(resp.json())

            filtered = [
                c for c in coins
                if c.get('price_change_percentage_24h') is not None
            ]

            cached_top_coins = sorted(filtered, key=lambda x: x['price_change_percentage_24h'], reverse=True)[:10]
            last_cache_time = now
        except Exception as e:
            bot.send_message(message.chat.id, "❌ خطا در دریافت داده‌ها از CoinGecko.")
            return

    usdt_price_irr = get_usdt_price_irr()
    text = "🚀 *۱۰ ارز با بیشترین رشد ۲۴ ساعته (از بین ۲۵۰ ارز اول بازار):*" \
    "اطلاعات از حافظه دریافت میگردد آپدیت اطلاعات هر 65 دقیقه"
    for coin in cached_top_coins:
        price_irr = coin['current_price'] * usdt_price_irr
        volume_irr = coin['total_volume'] * usdt_price_irr
        text += (
            f"\n🔹 *{coin['name']}* (`{coin['symbol'].upper()}`)\n"
            f"💰 قیمت: `{price_irr:,.0f}` ریال\n"
            f"📈 رشد: `{coin['price_change_percentage_24h']:+.2f}%`\n"
            f"🔄 حجم: `$ {coin['total_volume']:,.0f}`"
        )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# -------- دریافت قیمت با نماد --------
@bot.message_handler(func=lambda m: m.text == "📊 دریافت قیمت با نماد")
def ask_for_symbol(message: Message):
    bot.send_message(message.chat.id, "🔎 لطفاً نماد ارز (مثل btc یا eth) را وارد کنید:")
    broadcast_state[message.chat.id] = "awaiting_symbol"

@bot.message_handler(func=lambda m: broadcast_state.get(m.chat.id) == "awaiting_symbol")
def show_price_by_symbol(message: Message):
    symbol = message.text.strip().lower()
    broadcast_state.pop(message.chat.id, None)
    usdt_price_irr = get_usdt_price_irr()

    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 250,
            'page': 1,
            'price_change_percentage': '24h'
        }
        data = requests.get(url, params=params).json()
        coin = next((c for c in data if c['symbol'].lower() == symbol), None)

        if not coin:
            bot.send_message(message.chat.id, "❌ نماد یافت نشد.")
            return

        price_irr = coin['current_price'] * usdt_price_irr
        text = (
            f"💹 *{coin['name']}* (`{coin['symbol'].upper()}`)\n"
            f"💰 قیمت: `{price_irr:,.0f}` ریال\n"
            f"📈 رشد: `{coin['price_change_percentage_24h']:+.2f}%`\n"
            f"🔄 حجم: `$ {coin['total_volume']:,.0f}`"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    except Exception as e:
        bot.send_message(message.chat.id, "❌ خطا در دریافت اطلاعات.")

# -------- ارسال پیام همگانی --------
@bot.message_handler(func=lambda m: m.text == "📢 ارسال پیام همگانی" and m.from_user.id in ADMINS)
def ask_broadcast(message: Message):
    bot.send_message(message.chat.id, "✏️ پیام مورد نظر خود را ارسال کنید:")
    broadcast_state[message.chat.id] = "awaiting_broadcast"

@bot.message_handler(func=lambda m: broadcast_state.get(m.chat.id) == "awaiting_broadcast" and m.from_user.id in ADMINS)
def do_broadcast(message: Message):
    broadcast_state.pop(message.chat.id, None)
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    success = 0
    for (uid,) in users:
        try:
            bot.send_message(uid, f"📢 پیام ادمین:\n\n{message.text}")
            success += 1
        except:
            continue
    bot.send_message(message.chat.id, f"✅ پیام به {success} کاربر ارسال شد.")

# -------- تعداد کاربران --------
@bot.message_handler(func=lambda m: m.text == "👥 تعداد کاربران" and m.from_user.id in ADMINS)
def show_users(message: Message):
    total = count_users()
    bot.send_message(message.chat.id, f"👥 *تعداد کاربران:* `{total}`", parse_mode="Markdown")

# -------- خروج از حالت ادمین --------
@bot.message_handler(func=lambda m: m.text == "❌ خروج از حالت ادمین" and m.from_user.id in ADMINS)
def exit_admin(message: Message):
    user = User(message.from_user)
    bot.send_message(message.chat.id, "از حالت ادمین خارج شدید.", reply_markup=user.get_menu())

# -------- هندلر پیش‌فرض --------
@bot.message_handler(func=lambda m: True)
def fallback(message: Message):
    user = Admin(message.from_user) if message.from_user.id in ADMINS else User(message.from_user)
    tip = "لطفاً یکی از گزینه‌های منو را انتخاب کنید."
    bot.send_message(message.chat.id, tip, reply_markup=user.get_menu())

# -------- اجرای ربات --------
if __name__ == "__main__":
    print("Bot is running")
    bot.infinity_polling()
