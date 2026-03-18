import os
import telebot
import html
import time
from flask import Flask, render_template, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# 1. Инициализация и конфигурация
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

app = Flask(__name__)
# Путь к БД указываем абсолютно, чтобы избежать проблем при запуске через systemd
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bot = telebot.TeleBot(BOT_TOKEN)


# 2. Модели базы данных
class Guest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)  # Поле для защиты от спама
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Subscriber(db.Model):
    tg_id = db.Column(db.Integer, primary_key=True)


# Автоматическое создание таблиц при первом запуске
with app.app_context():
    db.create_all()


# 3. Web-интерфейс и API
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/rsvp', methods=['POST'])
def rsvp():
    data = request.json

    # Валидация входных данных
    if not data or not data.get('firstName') or not data.get('lastName') or not data.get('status'):
        return jsonify({'error': 'Пожалуйста, заполните все поля и выберите статус!'}), 400

    # Умное извлечение IP (Cloudflare -> Ngrok/Nginx -> Прямое подключение)
    if request.headers.get('CF-Connecting-IP'):
        user_ip = request.headers.get('CF-Connecting-IP')
    elif request.headers.get('X-Forwarded-For'):
    # Прокси часто передают цепочку IP, нам нужен первый (оригинальный клиент)
        user_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        user_ip = request.remote_addr

    # Проверка на дубликаты и спам (по IP)
    existing_entry = Guest.query.filter_by(ip_address=user_ip).first()
    if existing_entry:
        return jsonify({'error': 'Вы уже отправили ответ! Если нужно что-то изменить, напишите нам лично.'}), 400

    # Создание новой записи
    new_guest = Guest(
        first_name=data['firstName'].strip(),
        last_name=data['lastName'].strip(),
        status=data['status'],
        ip_address=user_ip
    )

    db.session.add(new_guest)
    db.session.commit()

    try:
        # Уведомление администратора
        icon = {"да": "✅", "возможно": "❓", "нет": "❌"}.get(data['status'].lower(), "⏺")
        admin_msg = (
            f"🔔 <b>Новый RSVP!</b>\n\n"
            f"👤 Гость: {new_guest.first_name} {new_guest.last_name}\n"
            f"📝 Статус: {new_guest.status} {icon}\n"
            #f"🌐 IP: <code>{user_ip}</code>"
        )
        bot.send_message(ADMIN_ID, admin_msg, parse_mode='HTML')

        return jsonify({'success': True, 'message': 'Очень вас ждем!'})

    except Exception as e:
        db.session.rollback()
        print(f"Ошибка БД: {e}")
        return jsonify({'error': 'Ошибка сервера при сохранении данных.'}), 500


# 4. Webhook для Telegram
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


# 5. Логика Telegram-бота
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)

    if message.chat.id == ADMIN_ID:
        markup.add(KeyboardButton("👥 Список гостей"), KeyboardButton("📢 Рассылка"))
        bot.send_message(message.chat.id, "💼 Панель управления свадьбой активна.", reply_markup=markup)
    else:
        markup.add(KeyboardButton("🔔 Подписаться на новости"))
        bot.send_message(
            message.chat.id,
            "Привет! Здесь будут важные новости о нашей свадьбе.💍 \nНажмите кнопку ниже, чтобы подписаться на рассылку новостей!",
            reply_markup=markup
        )


@bot.message_handler(func=lambda m: m.text == "🔔 Подписаться на новости")
def handle_subscription(message):
    with app.app_context():
        # Используем современный синтаксис Session.get()
        if not db.session.get(Subscriber, message.chat.id):
            db.session.add(Subscriber(tg_id=message.chat.id))
            db.session.commit()
            bot.send_message(message.chat.id, "✅ Вы успешно подписались!")
        else:
            bot.send_message(message.chat.id, "Вы уже в списке подписчиков 😉")


@bot.message_handler(func=lambda m: m.text in ["👥 Список гостей", "/guests"])
def get_guests(message):
    # ОТЛАДКА: Проверяем ID
    print(f"DEBUG: Вызван список гостей. Твой ID: {message.chat.id}, Ожидаемый ADMIN_ID: {ADMIN_ID}")

    if message.chat.id != ADMIN_ID:
        print("DEBUG: Отказ в доступе: ID не совпадает.")
        return

    with app.app_context():
        # Используем современный синтаксис запроса
        guests = db.session.execute(db.select(Guest).order_by(Guest.timestamp.desc())).scalars().all()
        subs_count = db.session.query(Subscriber).count()

        print(f"DEBUG: Найдено гостей в базе: {len(guests)}")

    # Отправляем общую статистику
    bot.send_message(
        ADMIN_ID,
        f"📋 <b>Всего ответов RSVP: {len(guests)}</b>\n📢 <b>Подписчиков: {subs_count}</b>",
        parse_mode='HTML'
    )

    if not guests:
        return

    for g in guests:
        try:
            icon = {"да": "✅", "возможно": "❓", "нет": "❌"}.get(g.status.lower(), "⏺")

            # Экранируем имена, чтобы символы <, > и & не ломали HTML-разметку Telegram
            safe_first_name = html.escape(g.first_name)
            safe_last_name = html.escape(g.last_name)

            txt = f"👤 <b>{safe_first_name} {safe_last_name}</b>\nСтатус: {g.status} {icon}"

            markup = InlineKeyboardMarkup()
            # Исправленный синтаксис удаления
            markup.add(InlineKeyboardButton("🗑 Удалить", callback_data=f"del_{g.id}"))

            bot.send_message(ADMIN_ID, txt, reply_markup=markup, parse_mode='HTML')
            # Защита от лимитов Telegram (Flood Control)
            time.sleep(0.005)
        except Exception as e:
            print(f"DEBUG: Ошибка при отправке сообщения гостя {g.id}: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def del_callback(call):
    if call.message.chat.id != ADMIN_ID: return

    gid = int(call.data.split('_')[1])

    with app.app_context():
        # НОВЫЙ СИНТАКСИС SQLAlchemy 2.0
        guest = db.session.get(Guest, gid)

        if guest:
            db.session.delete(guest)
            db.session.commit()

            # Зачеркиваем текст в телеграмме
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"<s>{call.message.text}</s>\n❌ <b>УДАЛЕНО</b>",
                parse_mode='HTML'
            )
            bot.answer_callback_query(call.id, "Запись удалена")
        else:
            bot.answer_callback_query(call.id, "Запись уже была удалена")

@bot.message_handler(func=lambda message: message.text in ["📢 Рассылка", "/notify"])
def start_broadcast(message):
    if message.chat.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "Введите текст сообщения или 'отмена':", parse_mode='HTML')
    bot.register_next_step_handler(msg, process_notify_step)


def process_notify_step(message):
    if message.text.lower() == 'отмена': return
    with app.app_context():
        subs = Subscriber.query.all()

    success = 0
    for s in subs:
        try:
            bot.send_message(s.tg_id, f"💌 <b>Сообщение от организаторов:</b>\n\n{message.text}", parse_mode='HTML')
            success += 1
        except:
            pass
    bot.send_message(ADMIN_ID, f"✅ Рассылка завершена: {success}/{len(subs)}")


if __name__ == '__main__':
    # Этот блок нужен только для локальной разработки и проверки верстки сайта.
    # Бот при таком запуске работать не будет (так как ожидаются POST-запросы от Telegram).
    print("Локальный сервер Flask запущен...")
    app.run(debug=True, host='0.0.0.0', port=5000)