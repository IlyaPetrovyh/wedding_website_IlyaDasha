import os
import telebot
from flask import Flask, render_template, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv

# Загружаем секреты из .env
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Инициализация Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных
db = SQLAlchemy(app)

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)


# --- МОДЕЛИ БАЗЫ ДАННЫХ ---
class Guest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Subscriber(db.Model):
    tg_id = db.Column(db.Integer, primary_key=True)

with app.app_context():
    db.create_all()


# --- МАРШРУТЫ САЙТА (WEB) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/rsvp', methods=['POST'])
def rsvp():
    data = request.json
    if not data or not data.get('firstName') or not data.get('lastName'):
        return jsonify({'error': 'Некорректные данные'}), 400

    new_guest = Guest(
        first_name=data['firstName'],
        last_name=data['lastName'],
        status=data['status']
    )

    db.session.add(new_guest)
    db.session.commit()

    # --- УВЕДОМЛЕНИЕ АДМИНИСТРАТОРУ ---
    try:
        status_text = data['status'].lower()
        if status_text == "да":
            icon = "✅"
        elif status_text == "возможно":
            icon = "❓"
        elif status_text == "нет":
            icon = "❌"
        else:
            icon = "⏺"

        # Формируем текст сообщения
        admin_message = (
            f"🔔 <b>Новая заявка RSVP!</b>\n\n"
            f"👤 Гость: {data['firstName']} {data['lastName']}\n"
            f"📝 Статус: {data['status']} {icon}"
        )

        # Отправляем сообщение (переменная ADMIN_ID у нас уже загружена из .env)
        bot.send_message(ADMIN_ID, admin_message, parse_mode='HTML')

    except Exception as e:
        # Логируем ошибку в консоль сервера, если сообщение не отправилось
        print(f"Не удалось отправить уведомление администратору: {e}")
    # ----------------------------------------------

    return jsonify({'success': True, 'message': 'Очень вас ждем!'})


# --- МАРШРУТ WEBHOOK (TELEGRAM) ---
# Используем токен в URL для безопасности, чтобы посторонние не могли слать фальшивые запросы
@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)


# --- ЛОГИКА БОТА ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Проверяем, кто пишет боту: админ или гость
    if message.chat.id == ADMIN_ID:
        markup.add(
            telebot.types.KeyboardButton("👥 Список гостей"),
            telebot.types.KeyboardButton("📢 Сделать рассылку")
        )
        bot.send_message(message.chat.id, "Панель администратора!", reply_markup=markup)
    else:
        markup.add(telebot.types.KeyboardButton("Подписаться на рассылку"))
        bot.send_message(
            message.chat.id,
            "Привет! Я бот свадьбы Ильи и Даши 💍\nНажмите кнопку ниже, чтобы подписаться на рассылку новостей!",
            reply_markup=markup
        )

# Обработка подписки для гостей
@bot.message_handler(func=lambda message: message.text == "Подписаться на рассылку")
def handle_subscription(message):
    # Работаем с БД через Flask-SQLAlchemy (в контексте приложения)
    with app.app_context():
        exists = Subscriber.query.get(message.chat.id)
        if not exists:
            new_sub = Subscriber(tg_id=message.chat.id)
            db.session.add(new_sub)
            db.session.commit()
            bot.send_message(message.chat.id, "✅ Вы успешно подписались на уведомления!")
        else:
            bot.send_message(message.chat.id, "Вы уже подписаны на обновления 😉")

@bot.message_handler(func=lambda message: message.text in ["👥 Список гостей", "/guests"])
def get_guests(message):
    if message.chat.id != ADMIN_ID:
        return

    with app.app_context():
        guests = Guest.query.all()

    if not guests:
        bot.send_message(message.chat.id, "Список гостей пока пуст.")
        return

    response = "📋 <b>Список гостей с сайта:</b>\n\n"
    for idx, guest in enumerate(guests, 1):
        status = guest.status.lower()
        # Маршрутизация иконок в зависимости от статуса
        if status == "да":
            icon = "✅"
        elif status == "возможно":
            icon = "❓"
        elif status == "нет":
            icon = "❌"
        else:
            icon = "⏺"

        response += f"{idx}. {guest.first_name} {guest.last_name} — {guest.status} {icon}\n"

    bot.send_message(message.chat.id, response, parse_mode='HTML')

#Интерактивная рассылка с обратной связью (Шаг 1)
@bot.message_handler(func=lambda message: message.text in ["📢 Сделать рассылку", "/notify"])
def start_notify(message):
    if message.chat.id != ADMIN_ID:
        return

    # Запрашиваем текст и переводим бота в режим ожидания следующего сообщения
    msg = bot.send_message(
        message.chat.id,
        "Введите текст сообщения для рассылки всем гостям:\n<i>(Для отмены напишите 'отмена')</i>",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, process_notify_step)

    # Обработка рассылки (Шаг 2)
def process_notify_step(message):
        text = message.text

        if text.lower() == 'отмена':
            bot.send_message(message.chat.id, "Рассылка отменена.")
            return

        with app.app_context():
            subscribers = Subscriber.query.all()

        count = 0
        for sub in subscribers:
            try:
                bot.send_message(sub.tg_id, f"🔔 <b>Важное обновление:</b>\n\n{text}", parse_mode='HTML')
                count += 1
            except Exception as e:
                # Если гость заблокировал бота, API выбросит исключение.
                # Мы его перехватываем, чтобы цикл не прервался.
                pass

        bot.send_message(message.chat.id,
                         f"✅ Рассылка успешно завершена.\nСообщение получили: {count} чел. из {len(subscribers)}.")


if __name__ == '__main__':
    # Снимаем Webhook на случай перезапуска
    bot.remove_webhook()
    # Если мы запускаем локально, Webhook работать не будет без туннеля (например ngrok).
    # В боевых условиях раскомментируй строку ниже и укажи свой реальный домен:
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}")

    print("Приложение запущено...")
    app.run(debug=True, host='0.0.0.0', port=5000)