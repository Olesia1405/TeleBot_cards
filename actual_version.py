import random
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

print('Start telegram bot...')

state_storage = StateMemoryStorage()
token_bot = os.getenv('TELEGRAM_TOKEN')
bot = TeleBot(token_bot, state_storage=state_storage)

db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')

conn = psycopg2.connect(
    dbname=db_name,
    user=db_user,
    password=db_password,
    host=db_host,
    port=db_port
)
cursor = conn.cursor()

class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'

class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    add_word_state = State()  # Новое состояние для добавления слова
    delete_word_state = State()  # Новое состояние для удаления слова

def add_user_to_db(user_id, username):
    cursor.execute("INSERT INTO users (id, username) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING", (user_id, username))
    conn.commit()

def add_word_to_db(user_id, english_word, russian_word):
    english_word = english_word.lower()
    cursor.execute("SELECT id FROM words WHERE english_word = %s AND (user_id IS NULL OR user_id = %s)", (english_word, user_id))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO words (english_word, russian_word, user_id) VALUES (%s, %s, %s) RETURNING id", 
                       (english_word, russian_word.lower(), user_id))
        word_id = cursor.fetchone()[0]
        cursor.execute("INSERT INTO user_words (user_id, word_id) VALUES (%s, %s)", (user_id, word_id))
        conn.commit()
    else:
        bot.send_message(user_id, f"Слово '{english_word}' уже существует.")

def delete_word_from_db(user_id, english_word):
    english_word = english_word.lower()
    cursor.execute("""
        DELETE FROM words 
        WHERE id = (
            SELECT w.id FROM words w 
            JOIN user_words uw ON w.id = uw.word_id 
            WHERE uw.user_id = %s AND w.english_word = %s
        )
    """, (user_id, english_word))
    conn.commit()

def get_random_words(user_id, limit=4):
    cursor.execute("""
        SELECT english_word, russian_word 
        FROM (
            SELECT w.english_word, w.russian_word 
            FROM words w 
            LEFT JOIN user_words uw ON w.id = uw.word_id 
            WHERE w.user_id IS NULL OR uw.user_id = %s
        ) AS user_words
        ORDER BY RANDOM()
        LIMIT %s
    """, (user_id, limit))
    return cursor.fetchall()

@bot.message_handler(commands=['start'])
def start_message(message):
    cid = message.chat.id
    add_user_to_db(cid, message.chat.username)
    bot.send_message(cid, "Hello, stranger, let's study English...")
    create_cards(message)

@bot.message_handler(commands=['cards'])
def create_cards(message):
    cid = message.chat.id
    words = get_random_words(cid)
    if words:
        target_word, translate = words.pop()
        other_words = [word[0] for word in words]
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
    bot.set_state(message.from_user.id, MyStates.add_word_state, message.chat.id)

@bot.message_handler(state=MyStates.add_word_state)
def save_word(message):
    cid = message.chat.id
    try:
        english_word, russian_word = map(str.strip, message.text.split(','))
        add_word_to_db(cid, english_word, russian_word)
        bot.send_message(cid, f"Word '{english_word.lower()}' with translation '{russian_word.lower()}' added.")
    except ValueError:
        bot.send_message(cid, "Invalid format. Please use 'English, Russian'.")
    bot.delete_state(message.from_user.id, cid)

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    bot.send_message(message.chat.id, "Send the word in English you want to delete.")
    bot.set_state(message.from_user.id, MyStates.delete_word_state, message.chat.id)

@bot.message_handler(state=MyStates.delete_word_state)
def remove_word(message):
    cid = message.chat.id
    english_word = message.text.strip()
    delete_word_from_db(cid, english_word)
    bot.send_message(cid, f"Word '{english_word.lower()}' deleted.")
    bot.delete_state(message.from_user.id, cid)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text.lower()
    cid = message.chat.id
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

if __name__ == '__main__':
    bot.infinity_polling(skip_pending=True)
