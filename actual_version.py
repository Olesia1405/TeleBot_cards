import os
import random
import psycopg2
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from dotenv import load_dotenv

print('Start telegram bot...')

load_dotenv('tg_tok.env')
TOKEN = os.environ['TOKEN']


state_storage = StateMemoryStorage()
token_bot = 'YOUR_BOT_TOKEN'
bot = TeleBot(TOKEN, state_storage=state_storage)

class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'

class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


# Подключение к базе данных
conn = psycopg2.connect(
    dbname='translate',
    user='postgres',
    password=os.environ['password_db'],
    host='localhost',
    port='5432'
)
cursor = conn.cursor()

def add_word_to_db(user_id, english_word, russian_word):
    cursor.execute("INSERT INTO words (english_word, russian_word, user_id) VALUES (%s, %s, %s)",
                   (english_word, russian_word, user_id))
    conn.commit()

def delete_word_from_db(user_id, english_word):
    cursor.execute("DELETE FROM words WHERE user_id = %s AND english_word = %s", (user_id, english_word))
    conn.commit()

def get_random_word(user_id):
    cursor.execute("SELECT english_word, russian_word FROM words WHERE user_id IS NULL OR user_id = %s ORDER BY RANDOM() LIMIT 1", (user_id,))
    return cursor.fetchone()

def get_random_words(user_id, exclude_word):
    cursor.execute("SELECT english_word FROM words WHERE (user_id IS NULL OR user_id = %s) AND english_word != %s ORDER BY RANDOM() LIMIT 3", (user_id, exclude_word))
    return [row[0] for row in cursor.fetchall()]


@bot.message_handler(commands=['start'])
def start_message(message):
    cid = message.chat.id
    bot.send_message(cid, "Hello, stranger, let study English...")

@bot.message_handler(commands=['cards'])
def create_cards(message):
    cid = message.chat.id
    word_pair = get_random_word(cid)
    if word_pair:
        target_word, translate = word_pair
        other_words = get_random_words(cid, target_word)
        options = [target_word] + other_words
        random.shuffle(options)
        
        markup = types.ReplyKeyboardMarkup(row_width=2)
        for option in options:
            markup.add(types.KeyboardButton(option))
        
        markup.add(types.KeyboardButton(Command.NEXT))
        markup.add(types.KeyboardButton(Command.ADD_WORD))
        markup.add(types.KeyboardButton(Command.DELETE_WORD))
        
        bot.send_message(cid, f"Выбери перевод слова:\n🇷🇺 {translate}", reply_markup=markup)
        bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['target_word'] = target_word
            data['translate_word'] = translate
            data['other_words'] = other_words
    else:
        bot.send_message(cid, "No words available. Please add new words.")

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)

@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    bot.send_message(message.chat.id, "Send the word in English and its translation in Russian separated by a comma.")
    bot.set_state(message.from_user.id, MyStates.another_words, message.chat.id)

@bot.message_handler(state=MyStates.another_words)
def save_word(message):
    cid = message.chat.id
    try:
        english_word, russian_word = map(str.strip, message.text.split(','))
        add_word_to_db(cid, english_word, russian_word)
        bot.send_message(cid, f"Word '{english_word}' with translation '{russian_word}' added.")
    except ValueError:
        bot.send_message(cid, "Invalid format. Please use 'English, Russian'.")
    bot.delete_state(message.from_user.id, cid)

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    bot.send_message(message.chat.id, "Send the word in English you want to delete.")
    bot.set_state(message.from_user.id, MyStates.another_words, message.chat.id)

@bot.message_handler(state=MyStates.another_words)
def remove_word(message):
    cid = message.chat.id
    english_word = message.text.strip()
    delete_word_from_db(cid, english_word)
    bot.send_message(cid, f"Word '{english_word}' deleted.")
    bot.delete_state(message.from_user.id, cid)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    cid = message.chat.id
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        translate_word = data['translate_word']
        if text == target_word:
            bot.send_message(cid, f"Отлично! ❤\n{target_word} -> {translate_word}")
            create_cards(message)
        else:
            bot.send_message(cid, "Допущена ошибка! Попробуй ещё раз.")
            create_cards(message)

bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)
