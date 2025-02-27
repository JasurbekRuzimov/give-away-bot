import telebot
import random
import openpyxl
import json
import os
import pandas as pd
from telebot import types
from unidecode import unidecode


API_TOKEN = '7661814317:AAHUOBKSXMy8UQsgYqOvLLEjcUth5qwDM00'  
bot = telebot.TeleBot(API_TOKEN)

ADMIN_USERNAME = "Ruzimov_Jasurbek"
CHANNEL_USERNAME = '@RuzimovDev'

USERS_FILE = 'users.json'
WINNERS_FILE = 'winners.json'

def load_users():
    try:
        with open(USERS_FILE, 'r') as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_users():
    with open(USERS_FILE, 'w') as file:
        json.dump(users, file, indent=4)

users = load_users()
previous_winners = []

def is_admin(message):
    return message.from_user.username == ADMIN_USERNAME

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    join_button = types.InlineKeyboardButton(text="Kanalga ulanish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
    join_now_button = types.InlineKeyboardButton(text="Giveawayda qatnashish", callback_data="join")
    markup.add(join_button, join_now_button)

    bot.send_message(
        message.chat.id,
        f"Assalomu alaykum, {sanitize_text(message.from_user.first_name)}! 🎉\n\n"
        f"📚 Giveaway’da ishtirok etish uchun quyidagilarni bajaring:\n"
        f"1️⃣ Kanalga obuna bo‘ling.\n"
        f"2️⃣ Giveaway tugmasini bosing.\n\n"
        f"G‘olib tasodifiy tanlanadi. Omad tilaymiz! 😊",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "join")
def join(call):
    try:
        user_status = bot.get_chat_member(CHANNEL_USERNAME, call.message.chat.id).status
        if user_status in ['member', 'administrator', 'creator']:
            if any(user.get("id") == call.message.chat.id for user in users):
                bot.send_message(call.message.chat.id, "⚠️ Siz allaqachon ro‘yxatdan o‘tgansiz!")
            else:
                bot.send_message(call.message.chat.id, "🔸 Iltimos, ismingizni yuboring.")
                bot.register_next_step_handler(call.message, get_user_first_name)
        else:
            bot.send_message(call.message.chat.id, "❌ Avval kanalga obuna bo‘ling!")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Xatolik yuz berdi. Xato: {e}")

def get_user_first_name(message):
    first_name = sanitize_text(message.text)
    bot.send_message(message.chat.id, "🔸 Iltimos, familiyangizni yuboring.")
    bot.register_next_step_handler(message, get_user_last_name, first_name)

def get_user_last_name(message, first_name):
    last_name = sanitize_text(message.text)
    bot.send_message(message.chat.id, "🔸 Iltimos, telefon raqamingizni yuboring.", reply_markup=phone_number_markup())
    bot.register_next_step_handler(message, get_user_phone_number, first_name, last_name)

def get_user_phone_number(message, first_name, last_name):
    if message.contact is None:
        bot.send_message(message.chat.id, "⚠️ Iltimos, telefon raqamingizni to‘g‘ri yuboring.")
        bot.register_next_step_handler(message, get_user_phone_number, first_name, last_name)
    else:
        full_phone_number = message.contact.phone_number
        masked_phone_number = "****" + full_phone_number[-4:]

        username = message.from_user.username or "Username mavjud emas"
        user = {
            "id": message.chat.id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "full_phone_number": full_phone_number,
            "masked_phone_number": masked_phone_number
        }

        if any(existing_user["id"] == user["id"] for existing_user in users):
            bot.send_message(message.chat.id, "⚠️ Siz allaqachon ro‘yxatdasiz!")
        else:
            users.append(user)
            save_users()
            bot.send_message(message.chat.id, f"✅ Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!")

def phone_number_markup():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    button = types.KeyboardButton("📱 Telefon raqamini yuboring", request_contact=True)
    markup.add(button)
    return markup

@bot.message_handler(commands=['winners'])
def select_winners(message):
    if not is_admin(message):
        bot.send_message(message.chat.id, "❌ Sizda bu buyruqdan foydalanish huquqi yo‘q!")
        return

    global previous_winners
    num_winners = 2  
    eligible_users = [user for user in users if user["id"] not in [w["id"] for w in previous_winners]]

    if len(eligible_users) < num_winners:
        bot.send_message(message.chat.id, "⚠️ Yetarlicha ishtirokchilar yo‘q!")
        return

    selected_winners = random.sample(eligible_users, num_winners)
    winner_text = "🎉 G‘oliblar:\n"

    for i, winner in enumerate(selected_winners, 1):
        winner_text += f"{i}. {winner['first_name']} {winner['last_name']} - Telefon: {winner['masked_phone_number']} 🎉\n"

    bot.send_message(message.chat.id, winner_text)
    previous_winners = selected_winners  

@bot.message_handler(commands=['export'])
def export_users(message):
    if not is_admin(message):
        bot.send_message(message.chat.id, "❌ Sizda bu buyruqdan foydalanish huquqi yo‘q!")
        return

    df = pd.DataFrame(users)
    excel_file = "users.xlsx"
    df.to_excel(excel_file, index=False)

    with open(excel_file, "rb") as f:
        bot.send_document(message.chat.id, f)

def sanitize_text(text):
    import re
    return unidecode(re.sub(r'[^\w\s]', '', text))

if __name__ == "__main__":
    bot.remove_webhook()
    bot.polling(none_stop=True)
