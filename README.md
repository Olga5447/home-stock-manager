# home-stock-manager
 "Backend сервис для управления домашними запасами"
#  Менеджер домашних запасов

Backend-сервис для управления домашними запасами продуктов и бытовых товаров.

##  Требования

- Python 3.11+
- pip

##  Установка и запуск
python -m venv venv # Создание виртуального окружения

cd home-stock-manager # переход в папку проекта

venv\Scripts\activate # Активация виртуального окружения

cd home-stock-manager # переход в папку проекта

pip install -r requirements.txt # Установка зависимостей

python manage.py makemigrations
python manage.py migrate # Применить миграции

python manage.py createsuperuser  # Создание суперпользователя

python manage.py runserver # Запуск сервера


http://127.0.0.1:8000/admin/

http://127.0.0.1:8000/docs/
