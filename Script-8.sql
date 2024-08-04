CREATE TABLE words (
    id SERIAL PRIMARY KEY,
    english_word VARCHAR(255) NOT NULL,
    russian_word VARCHAR(255) NOT NULL,
    user_id BIGINT
);

CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(255)
);


INSERT INTO words (english_word, russian_word, user_id) VALUES
('Red', 'Красный', NULL),
('Blue', 'Синий', NULL),
('Green', 'Зелёный', NULL),
('Yellow', 'Жёлтый', NULL),
('Black', 'Чёрный', NULL),
('White', 'Белый', NULL),
('I', 'Я', NULL),
('You', 'Ты', NULL),
('We', 'Мы', NULL),
('They', 'Они', NULL);
