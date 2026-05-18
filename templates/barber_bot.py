
import os
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('قص شعر')
    btn2 = types.KeyboardButton('حلاقة ذقن')
    btn3 = types.KeyboardButton('مواعيدي')
    markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, "مرحباً بك في صالون الحلاقة! اختر الخدمة المطلوبة:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    bot.reply_to(message, f"تم استلام طلبك لـ {message.text}. سنقوم بالتواصل معك قريباً.")

bot.polling(none_stop=True)
