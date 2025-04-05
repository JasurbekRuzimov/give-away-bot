import telebot
import random
import pandas as pd
import os
import psycopg2
from telebot import types
from unidecode import unidecode
from dotenv import load_dotenv


load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
DATABASE_URL = os.getenv("DATABASE_URL ")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

bot = telebot.TeleBot(API_TOKEN)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def create_users_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            full_phone_number TEXT,
            masked_phone_number TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

create_users_table()

def is_admin(message):
    return message.from_user.username == ADMIN_USERNAME

def sanitize_text(text):
    import re
    return unidecode(re.sub(r'[^\w\s]', '', text))

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    join_button = types.InlineKeyboardButton(text="Kanalga ulanish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    join_now_button = types.InlineKeyboardButton(text="Giveawayda qatnashish", callback_data="join")
    markup.add(join_button, join_now_button)

    bot.send_message(
        message.chat.id,
        f"Assalomu alaykum, {sanitize_text(message.from_user.first_name)}! 🎉\n\n"
        f"📚 Giveaway’da ishtirok etish uchun kanalga a'zo bo‘ling va ro‘yxatdan o‘ting!",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "join")
def join(call):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE id = %s", (call.message.chat.id,))
    existing_user = cur.fetchone()

    if existing_user:
        bot.send_message(call.message.chat.id, "✅ Siz allaqachon ro‘yxatdan o'tgansiz!")
    else:
        user_status = bot.get_chat_member(CHANNEL_USERNAME, call.message.chat.id).status
        if user_status in ['member', 'administrator', 'creator']:
            bot.send_message(call.message.chat.id, "🔸 Iltimos, ismingizni yuboring.")
            bot.register_next_step_handler(call.message, get_user_first_name)
        else:
            bot.send_message(call.message.chat.id, "❌ Avval kanalga obuna bo‘ling!")

    cur.close()
    conn.close()

def get_user_first_name(message):
    first_name = sanitize_text(message.text)
    bot.send_message(message.chat.id, "🔸 Iltimos, familiyangizni yuboring.")
    bot.register_next_step_handler(message, get_user_last_name, first_name)

def get_user_last_name(message, first_name):
    last_name = sanitize_text(message.text)
    bot.send_message(message.chat.id, "🔸 Iltimos, telefon raqamingizni yuboring.", reply_markup=phone_number_markup())
    bot.register_next_step_handler(message, get_user_phone_number, first_name, last_name)

def get_user_phone_number(message, first_name, last_name):
    if not message.contact:
        bot.send_message(message.chat.id, "⚠️ Iltimos, telefon raqamingizni to‘g‘ri yuboring.")
        bot.register_next_step_handler(message, get_user_phone_number, first_name, last_name)
        return

    full_phone_number = message.contact.phone_number
    masked_phone_number = "****" + full_phone_number[-4:]
    username = message.from_user.username or "Username mavjud emas"

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING", 
                (message.chat.id, username, first_name, last_name, full_phone_number, masked_phone_number))
    conn.commit()
    cur.close()
    conn.close()

    bot.send_message(message.chat.id, "✅ Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!")

def phone_number_markup():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    button = types.KeyboardButton("📱 Telefon raqamini yuboring", request_contact=True)
    markup.add(button)
    return markup

@bot.message_handler(commands=['winners'])
def request_winner_count(message):
    if not is_admin(message):
        bot.send_message(message.chat.id, "❌ Sizda bu buyruqdan foydalanish huquqi yo‘q!")
        return

    bot.send_message(message.chat.id, "🏆 Nechta odam g‘olib bo‘lishi kerak?")
    bot.register_next_step_handler(message, select_winners)

def select_winners(message):
    try:
        num_winners = int(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Iltimos, faqat son kiriting!")
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()

    if len(users) < num_winners:
        bot.send_message(message.chat.id, "⚠️ Yetarlicha ishtirokchilar yo‘q!")
        return

    winners = random.sample(users, num_winners)
    winner_text = "🎉 G‘oliblar:\n"
    
    for i, winner in enumerate(winners, 1):
        winner_text += f"{i}. {winner[2]} {winner[3]} - Telefon: {winner[5]} 🎉\n"
        bot.send_message(winner[0], f"🎉 Tabriklaymiz! Siz Book Party g‘oliblaridan birisiz! 🏆\n"
                                    f"Sizni g‘alaba bilan tabriklaymiz!\n"
                                    f"📞 Telefon: {winner[5]}\n"
                                    f"📩 Tez orada siz bilan bog‘lanamiz!")

    bot.send_message(message.chat.id, "🏆 G‘oliblar e’lon qilindi!")
    bot.send_message(f"@{CHANNEL_USERNAME[1:]}", "🏆 G‘oliblar e’lon qilindi!\n" + winner_text)

@bot.message_handler(commands=['export'])
def export_users(message):
    if not is_admin(message):
        bot.send_message(message.chat.id, "❌ Sizda bu buyruqdan foydalanish huquqi yo‘q!")
        return

    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM users", conn)
    conn.close()

    excel_file = "users.xlsx"
    df.to_excel(excel_file, index=False)

    with open(excel_file, "rb") as f:
        bot.send_document(message.chat.id, f)

if __name__ == "__main__":
    bot.polling(none_stop=True)
