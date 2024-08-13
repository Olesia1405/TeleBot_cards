CREATE TABLE users (
    id BIGINT PRIMARY KEY, -- ID пользователя из Telegram
    username TEXT
);

CREATE TABLE words (
    id SERIAL PRIMARY KEY,
    english_word TEXT NOT NULL,
    russian_word TEXT NOT NULL,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE -- ID пользователя или NULL для общих слов
);

CREATE TABLE user_words (
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    word_id INTEGER REFERENCES words(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, word_id)
);
