import telebot
import random
import openpyxl
import json
import os
from telebot import types
from unidecode import unidecode

API_TOKEN = 'write your bot token'  
CHANNEL_USERNAME = 'write telegram channel username with @'

bot = telebot.TeleBot(API_TOKEN)

USERS_FILE = 'users.json'

def load_users():
    try:
        with open(USERS_FILE, 'r') as file:
            data = json.load(file)
            if isinstance(data, list):
                return data
            else:
                return []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_users():
    try:
        with open(USERS_FILE, 'w') as file:
            json.dump(users, file, indent=4)
    except Exception as e:
        print(f"Error saving users: {e}")

users = load_users()

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
        if call.message and call.message.chat:
            user_status = bot.get_chat_member(CHANNEL_USERNAME, call.message.chat.id).status
            if user_status in ['member', 'administrator', 'creator']:
                if any(user.get("id") == call.message.chat.id for user in users):
                    bot.send_message(call.message.chat.id, "⚠️ Siz allaqachon ro‘yxatdan o‘tgansiz!")
                else:
                    bot.send_message(call.message.chat.id, "🔸 Iltimos, ismingizni yuboring.")
                    bot.register_next_step_handler(call.message, get_user_first_name)
            else:
                bot.send_message(call.message.chat.id, "❌ Avval kanalga obuna bo‘ling!")
        else:
            raise ValueError("No message or chat data found in callback query.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Xatolik yuz berdi. Keyinroq urinib ko‘ring. Xato: {e}")

def get_user_first_name(message):
    if message.contact is not None:
        bot.send_message(message.chat.id, "⚠️ Iltimos, ism o'rniga telefon raqamini yubormang. Ismingizni yozing.")
        bot.register_next_step_handler(message, get_user_first_name)
    else:
        first_name = sanitize_text(message.text)
        bot.send_message(message.chat.id, "🔸 Iltimos, telefon raqamingizni yuboring (telefonni yuboring).", reply_markup=phone_number_markup())
        bot.register_next_step_handler(message, get_user_phone_number, first_name)

def get_user_phone_number(message, first_name):
    if message.contact is None:
        bot.send_message(message.chat.id, "⚠️ Iltimos, telefon raqam o'rniga ism yubormang. Telefon raqamingizni yuboring.")
        bot.register_next_step_handler(message, get_user_phone_number, first_name)
    else:
        phone_number = message.contact.phone_number
        if len(phone_number) < 10:
            bot.send_message(message.chat.id, "⚠️ Telefon raqami noto‘g‘ri kiritildi. Iltimos, to‘g‘ri raqam yuboring.")
            bot.register_next_step_handler(message, get_user_phone_number, first_name)
            return

        username = message.from_user.username or "Username mavjud emas"
        user = {
            "id": message.chat.id,
            "username": username,
            "first_name": first_name,
            "phone_number": phone_number
        }

        if any(existing_user["id"] == user["id"] for existing_user in users):
            bot.send_message(message.chat.id, "⚠️ Siz allaqachon ro‘yxatdasiz!")
        else:
            users.append(user)
            save_users()
            bot.send_message(message.chat.id, f"✅ Siz muvaffaqiyatli ro‘yxatga kiritildingiz!\n\n"
                                              f"Ism: {first_name}\nUsername: {username}\nTelefon raqami: {phone_number}")

def phone_number_markup():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    button = types.KeyboardButton("📱 Telefon raqamini yuboring", request_contact=True)
    markup.add(button)
    return markup

@bot.message_handler(commands=['export'])
def export(message):
    try:
        filename = "giveaway_users.xlsx"
        if os.path.exists(filename):
            os.remove(filename) 

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Giveaway Users"
        sheet.append(["ID", "Username", "First Name", "Phone Number"])

        for user in users:
            sheet.append([user["id"], user["username"], user["first_name"], user["phone_number"]])

        workbook.save(filename)
        with open(filename, "rb") as file:
            bot.send_document(message.chat.id, file)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Fayl eksport qilishda xatolik yuz berdi. Xato: {e}")

@bot.message_handler(commands=['winners'])
def select_winners(message):
    num_winners = 1 

    if len(users) <= num_winners:
        bot.send_message(message.chat.id, f"⚠️ Hozirda g'oliblarni aniqlash uchun kamida {num_winners} ishtirokchi kerak.")
        return

    selected_winners = random.sample(users, num_winners)
    winner_text = "🎉 G‘oliblar:\n"

    for i, winner in enumerate(selected_winners, 1):
        winner_text += f"{i}. @{winner['username']} ({winner['first_name']}) - Telefon: {winner['phone_number']} 🎉\n"

    try:
        bot.send_message(CHANNEL_USERNAME, winner_text)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Kanalga xabar yuborishda xatolik yuz berdi. Xato: {e}")
        print(f"Kanalga xabar yuborishda xatolik: {e}")

    for winner in selected_winners:
        try:
            bot.send_message(
                winner['id'],
                f"🎉 Tabriklaymiz! Siz g‘olib bo‘ldingiz, {winner['first_name']}! 🏆\n"
                f"Sovg‘angizni olish uchun biz bilan bog‘laning.\nTelegram: @Username"
            )
        except Exception as e:
            print(f"G'olibga xabar yuborishda xatolik ({winner['username']}): {e}")

def sanitize_text(text):
    import re
    return unidecode(re.sub(r'[^\w\s]', '', text))

bot.polling()