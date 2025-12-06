#!/bin/bash

echo "Запуск приложения Что? Где? Когда? Шпаргалка"

# Создание виртуального окружения (если необходимо)
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Обновление зависимостей
echo "Установка/обновление зависимостей..."
pip install -r requirements.txt

# Запуск скрапера для получения данных
echo "Сбор вопросов с сайта..."
python scraper.py

# Запуск веб-сервера
echo "Запуск веб-сервера..."
echo "Откройте в браузере http://localhost:5000"
python app.py