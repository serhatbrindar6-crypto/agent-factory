
import os
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('قائمة الطعام')
    btn2 = types.KeyboardButton('طلب جديد')
    btn3 = types.KeyboardButton('موقعنا')
    markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, "أهلاً بك في مطعمنا! كيف يمكننا خدمتك اليوم؟", reply_markup=markup)

bot.polling(none_stop=True)
