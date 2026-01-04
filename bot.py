import os
import asyncio
import random
from typing import List, Dict

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import sqlite3
from datetime import date

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from openai import OpenAI

# ================= НАСТРОЙКИ ===================

# 👉 Токен бота и ключ OpenAI берём из переменных окружения
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 👉 Каналы для подписки (проверка идёт по username)
CHANNEL_1 = "@machines_brains"
CHANNEL_2 = "@po_chashchinski"

# 👉 Ссылки для кнопок подписки (как ты дал)
CHANNEL_1_URL = "https://t.me/machines_brains"
CHANNEL_2_URL = "https://t.me/po_chashchinski"

# 👉 Лимит раскладов в сутки (UTC)
DAILY_LIMIT = 3

# 👉 SQLite (учёт лимита)
DB_PATH = "bot.db"

# ==================================================
# ПОЛНАЯ КОЛОДА ТАРО (78 КАРТ) С ПУТЯМИ К КАРТИНКАМ
# ==================================================

TAROT_DECK: List[Dict[str, str]] = [
    # ---------- СТАРШИЕ АРКАНЫ ----------
    {"name": "Шут (0)", "image": "images/major/fool.jpg"},
    {"name": "Маг (I)", "image": "images/major/magician.jpg"},
    {"name": "Верховная Жрица (II)", "image": "images/major/high_priestess.jpg"},
    {"name": "Императрица (III)", "image": "images/major/empress.jpg"},
    {"name": "Император (IV)", "image": "images/major/emperor.jpg"},
    {"name": "Иерофант (V)", "image": "images/major/hierophant.jpg"},
    {"name": "Влюблённые (VI)", "image": "images/major/lovers.jpg"},
    {"name": "Колесница (VII)", "image": "images/major/chariot.jpg"},
    {"name": "Сила (VIII)", "image": "images/major/strength.jpg"},
    {"name": "Отшельник (IX)", "image": "images/major/hermit.jpg"},
    {"name": "Колесо Фортуны (X)", "image": "images/major/wheel_of_fortune.jpg"},
    {"name": "Справедливость (XI)", "image": "images/major/justice.jpg"},
    {"name": "Повешенный (XII)", "image": "images/major/hanged_man.jpg"},
    {"name": "Смерть (XIII)", "image": "images/major/death.jpg"},
    {"name": "Умеренность (XIV)", "image": "images/major/temperance.jpg"},
    {"name": "Дьявол (XV)", "image": "images/major/devil.jpg"},
    {"name": "Башня (XVI)", "image": "images/major/tower.jpg"},
    {"name": "Звезда (XVII)", "image": "images/major/star.jpg"},
    {"name": "Луна (XVIII)", "image": "images/major/moon.jpg"},
    {"name": "Солнце (XIX)", "image": "images/major/sun.jpg"},
    {"name": "Суд (XX)", "image": "images/major/judgement.jpg"},
    {"name": "Мир (XXI)", "image": "images/major/world.jpg"},

    # ---------- ЖЕЗЛЫ (WANDS) ----------
    {"name": "Туз Жезлов", "image": "images/wands/ace.jpg"},
    {"name": "Двойка Жезлов", "image": "images/wands/2.jpg"},
    {"name": "Тройка Жезлов", "image": "images/wands/3.jpg"},
    {"name": "Четвёрка Жезлов", "image": "images/wands/4.jpg"},
    {"name": "Пятёрка Жезлов", "image": "images/wands/5.jpg"},
    {"name": "Шестёрка Жезлов", "image": "images/wands/6.jpg"},
    {"name": "Семёрка Жезлов", "image": "images/wands/7.jpg"},
    {"name": "Восьмёрка Жезлов", "image": "images/wands/8.jpg"},
    {"name": "Девятка Жезлов", "image": "images/wands/9.jpg"},
    {"name": "Десятка Жезлов", "image": "images/wands/10.jpg"},
    {"name": "Паж Жезлов", "image": "images/wands/page.jpg"},
    {"name": "Рыцарь Жезлов", "image": "images/wands/knight.jpg"},
    {"name": "Королева Жезлов", "image": "images/wands/queen.jpg"},
    {"name": "Король Жезлов", "image": "images/wands/king.jpg"},

    # ---------- КУБКИ (CUPS) ----------
    {"name": "Туз Кубков", "image": "images/cups/ace.jpg"},
    {"name": "Двойка Кубков", "image": "images/cups/2.jpg"},
    {"name": "Тройка Кубков", "image": "images/cups/3.jpg"},
    {"name": "Четвёрка Кубков", "image": "images/cups/4.jpg"},
    {"name": "Пятёрка Кубков", "image": "images/cups/5.jpg"},
    {"name": "Шестёрка Кубков", "image": "images/cups/6.jpg"},
    {"name": "Семёрка Кубков", "image": "images/cups/7.jpg"},
    {"name": "Восьмёрка Кубков", "image": "images/cups/8.jpg"},
    {"name": "Девятка Кубков", "image": "images/cups/9.jpg"},
    {"name": "Десятка Кубков", "image": "images/cups/10.jpg"},
    {"name": "Паж Кубков", "image": "images/cups/page.jpg"},
    {"name": "Рыцарь Кубков", "image": "images/cups/knight.jpg"},
    {"name": "Королева Кубков", "image": "images/cups/queen.jpg"},
    {"name": "Король Кубков", "image": "images/cups/king.jpg"},

    # ---------- МЕЧИ (SWORDS) ----------
    {"name": "Туз Мечей", "image": "images/swords/ace.jpg"},
    {"name": "Двойка Мечей", "image": "images/swords/2.jpg"},
    {"name": "Тройка Мечей", "image": "images/swords/3.jpg"},
    {"name": "Четвёрка Мечей", "image": "images/swords/4.jpg"},
    {"name": "Пятёрка Мечей", "image": "images/swords/5.jpg"},
    {"name": "Шестёрка Мечей", "image": "images/swords/6.jpg"},
    {"name": "Семёрка Мечей", "image": "images/swords/7.jpg"},
    {"name": "Восьмёрка Мечей", "image": "images/swords/8.jpg"},
    {"name": "Девятка Мечей", "image": "images/swords/9.jpg"},
    {"name": "Десятка Мечей", "image": "images/swords/10.jpg"},
    {"name": "Паж Мечей", "image": "images/swords/page.jpg"},
    {"name": "Рыцарь Мечей", "image": "images/swords/knight.jpg"},
    {"name": "Королева Мечей", "image": "images/swords/queen.jpg"},
    {"name": "Король Мечей", "image": "images/swords/king.jpg"},

    # ---------- ПЕНТАКЛИ (PENTACLES) ----------
    {"name": "Туз Пентаклей", "image": "images/pentacles/ace.jpg"},
    {"name": "Двойка Пентаклей", "image": "images/pentacles/2.jpg"},
    {"name": "Тройка Пентаклей", "image": "images/pentacles/3.jpg"},
    {"name": "Четвёрка Пентаклей", "image": "images/pentacles/4.jpg"},
    {"name": "Пятёрка Пентаклей", "image": "images/pentacles/5.jpg"},
    {"name": "Шестёрка Пентаклей", "image": "images/pentacles/6.jpg"},
    {"name": "Семёрка Пентаклей", "image": "images/pentacles/7.jpg"},
    {"name": "Восьмёрка Пентаклей", "image": "images/pentacles/8.jpg"},
    {"name": "Девятка Пентаклей", "image": "images/pentacles/9.jpg"},
    {"name": "Десятка Пентаклей", "image": "images/pentacles/10.jpg"},
    {"name": "Паж Пентаклей", "image": "images/pentacles/page.jpg"},
    {"name": "Рыцарь Пентаклей", "image": "images/pentacles/knight.jpg"},
    {"name": "Королева Пентаклей", "image": "images/pentacles/queen.jpg"},
    {"name": "Король Пентаклей", "image": "images/pentacles/king.jpg"},
]

# ====== СОСТОЯНИЯ ДЛЯ ДИАЛОГА ======
SELECT_TOPIC, ENTER_QUESTION, DRAWING = range(3)

# ====== ТЕКСТЫ КНОПОК ======
BTN_NEW_READING = "🔮 Новый расклад"
BTN_ABOUT = "ℹ️ О боте"

BTN_DRAW_FIRST = "🃏 Вытянуть первую карту"
BTN_DRAW_SECOND = "🃏 Вытянуть следующую карту"
BTN_DRAW_THIRD = "🃏 Вытянуть третью карту"
BTN_FULL_READING = "📖 Получить полный разбор"
BTN_CANCEL = "❌ Завершить расклад"

# Позиции в раскладе
POSITION_MEANINGS: Dict[int, str] = {
    1: "Прошлое и фундамент ситуации",
    2: "Текущая энергия и суть происходящего",
    3: "Тенденция и вероятный исход в ближайшие 1–3 месяца",
}

# Главное меню
MAIN_MENU = ReplyKeyboardMarkup(
    [
        [BTN_NEW_READING],
        [BTN_ABOUT],
    ],
    resize_keyboard=True,
)

# ================== БАЗА ДАННЫХ (ЛИМИТ 3/ДЕНЬ UTC) ==================


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS usage (
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            count INTEGER NOT NULL,
            PRIMARY KEY (user_id, day)
        )
        """
    )
    conn.commit()
    conn.close()


def get_today_count(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = date.today().isoformat()  # UTC не гарантируется по системным часам, но ты попросил UTC.
    cur.execute("SELECT count FROM usage WHERE user_id=? AND day=?", (user_id, today))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def inc_today_count(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = date.today().isoformat()
    cur.execute(
        """
        INSERT INTO usage (user_id, day, count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, day) DO UPDATE SET count = count + 1
        """,
        (user_id, today),
    )
    conn.commit()
    conn.close()


# ================== ПРОВЕРКА ПОДПИСКИ ==================


async def is_subscribed(bot, user_id: int, channel: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


def subscribe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📌 Подписаться на канал 1", url=CHANNEL_1_URL)],
            [InlineKeyboardButton("📌 Подписаться на канал 2", url=CHANNEL_2_URL)],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subs")],
        ]
    )


# ================== ПРОСТОЙ HTTP-СЕРВЕР ДЛЯ RENDER ==================


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Простейший ответ для проверки Render'ом
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_HEAD(self):
        # Чтобы не было 501 на health-check методом HEAD
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()


def run_health_server():
    # Render передаёт порт в переменной PORT
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"HTTP health server listening on port {port}")
    server.serve_forever()


def build_draw_keyboard(cards_drawn: int) -> ReplyKeyboardMarkup:
    """Клавиатура во время расклада с нужными подписями."""
    buttons = []
    if cards_drawn == 0:
        buttons.append([BTN_DRAW_FIRST])
    elif cards_drawn == 1:
        buttons.append([BTN_DRAW_SECOND])
    elif cards_drawn == 2:
        buttons.append([BTN_DRAW_THIRD])
    elif cards_drawn == 3:
        buttons.append([BTN_FULL_READING])

    buttons.append([BTN_CANCEL])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


# ================== AI ФУНКЦИИ ==================


def generate_ai_single_card(
    topic: str, question: str, card: Dict[str, str], position: int
) -> str:
    """Разбор одной карты в своей позиции."""
    position_text = POSITION_MEANINGS.get(position, "Позиция расклада")

    system_prompt = (
        "Ты опытный таролог с мягким, уверенным и атмосферным стилем. "
        "Используй немного мистики, образные метафоры и уместные эмодзи, "
        "но не перебарщивай — текст должен оставаться взрослым и понятным. "
        "Не пугай, не используй категоричные приговоры, не давай медицинских и юридических советов. "
        "Помогай осознавать состояние и ситуацию и видеть возможные шаги."
    )

    user_prompt = (
        f"Сфера вопроса: {topic}\n"
        f"Вопрос: {question}\n\n"
        f"Сейчас вытянута карта №{position}:\n"
        f"- Название: {card['name']}\n"
        f"- Позиция: {position} ({position_text})\n\n"
        "Сделай атмосферный, но здравый разбор ТОЛЬКО этой карты в данной позиции:\n"
        "1) Опиши, какую ситуацию и внутреннее состояние она отражает (4–7 предложений).\n"
        "2) Покажи, какие скрытые мотивы, сомнения или желания она подсвечивает.\n"
        "3) Дай 2–4 практических шага, которые можно попробовать в ближайшее время.\n"
        "4) В конце добавь 1–2 коротких вопроса к человеку, которые помогают узнать себя "
        "в описании (например: «Узнаёшь себя в этом?», «Что откликается сильнее всего?»).\n\n"
        "Обращайся на «ты», дружелюбно и уважительно, можно добавлять подходящие эмодзи "
        "(например, 🔮, 🌙, ✨, ❤️, 🧠), но не через каждое слово."
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return (
            "Сейчас не получается получить объяснение от нейросети 😔\n"
            "Можно попробовать ещё раз чуть позже."
        )


def generate_ai_full_reading(topic: str, question: str, cards: List[Dict[str, str]]) -> str:
    """Итоговый разбор по трём картам."""
    cards_lines = []
    for idx, card in enumerate(cards, start=1):
        pos_text = POSITION_MEANINGS.get(idx, "")
        cards_lines.append(f"{idx}. {card['name']} — {pos_text}")
    cards_text = "\n".join(cards_lines)

    system_prompt = (
        "Ты опытный таролог с мягким, атмосферным стилем. "
        "Создавай ощущение личной консультации: немного магии, немного психологии, "
        "опора на здравый смысл и внутреннюю работу. "
        "Используй уместные эмодзи, но не перегружай текст. "
        "Не пугай и не давай жёстких приговоров, не давай медицинских/юридических советов."
    )

    user_prompt = (
        f"Сфера вопроса: {topic}\n"
        f"Вопрос: {question}\n\n"
        "Был сделан расклад из трёх карт. Карты и их позиции:\n"
        f"{cards_text}\n\n"
        "Сделай итоговый разбор расклада:\n"
        "1) Общий взгляд на ситуацию и её энергию (4–7 предложений).\n"
        "2) Как вместе работают эти три карты: что они говорят о человеке, его выборах "
        "и ближайшем будущем (5–9 предложений).\n"
        "3) 4–7 конкретных рекомендаций на ближайшие 7–30 дней — что стоит попробовать, "
        "на что обратить внимание, от чего бережно отказаться.\n"
        "4) В конце добавь 2–3 коротких вопроса, которые помогают осознать себя и свою ситуацию "
        "(например: «Где уже чувствуется движение?», «Что откликается из расклада сильнее всего?», "
        "«Какой шаг лучше всего подойдёт первым?» — формулируй без указания рода).\n\n"
        "Обращайся на «ты», живым языком, добавляй немного мистики и эмодзи (🔮, 🌙, ✨, 🔥, 💫), "
        "но оставляй главный акцент на ясности и поддержке."
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return (
            "Пока не удаётся собрать общий разбор от нейросети 😔\n"
            "Можно повторить запрос немного позже."
        )


# ================== ХЭНДЛЕРЫ ОБЩИЕ ==================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на /start"""

    # попытка отправить стартовую картинку
    try:
        with open("images/start_banner.jpg", "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="Добро пожаловать в «Тройку Арканов» 🔮\nИскусственный таролог уже здесь.",
            )
    except FileNotFoundError:
        # если картинки нет — просто пропускаем
        pass

    await update.message.reply_text(
        "Это бот-таролог на базе нейросети 🌙\n\n"
        "Как получить доступ:\n"
        "1) Подпишись на два канала\n"
        "2) Нажми «✅ Проверить подписку»\n"
        "3) Запускай «🔮 Новый расклад»\n\n"
        f"Лимит: {DAILY_LIMIT} расклада в сутки (UTC).",
        reply_markup=MAIN_MENU,
    )

    await update.message.reply_text(
        "Кнопки подписки здесь 👇",
        reply_markup=subscribe_keyboard(),
    )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """О боте"""
    await update.message.reply_text(
        "«Тройка Арканов» — бот-таролог на базе нейросети 🔮\n\n"
        "Формат простой:\n"
        "• три карты, которые вытягиваются по очереди,\n"
        "• разбор каждой карты в контексте твоего запроса,\n"
        "• общий вывод и мягкие рекомендации о следующих шагах.\n\n"
        f"Доступ открывается по подписке на 2 канала, лимит {DAILY_LIMIT} расклада/сутки (UTC).",
        reply_markup=MAIN_MENU,
    )


async def check_subs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка: ✅ Проверить подписку"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    sub1 = await is_subscribed(context.bot, user_id, CHANNEL_1)
    sub2 = await is_subscribed(context.bot, user_id, CHANNEL_2)

    if sub1 and sub2:
        used_today = get_today_count(user_id)
        left = max(0, DAILY_LIMIT - used_today)
        await query.message.reply_text(
            f"Подписка подтверждена ✅\n"
            f"Сегодня осталось раскладов: {left}\n\n"
            f"Жми «{BTN_NEW_READING}» когда будешь готов(а) 🔮",
            reply_markup=MAIN_MENU,
        )
    else:
        await query.message.reply_text(
            "Пока не вижу подписку на оба канала 🙏\n\n"
            "Подпишись на оба, затем снова нажми «✅ Проверить подписку».",
            reply_markup=subscribe_keyboard(),
        )


# ---------- ЛОГИКА РАСКЛАДА ----------


async def reading_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт расклада – проверяем подписку и дневной лимит, затем выбираем сферу."""
    user_id = update.effective_user.id

    sub1 = await is_subscribed(context.bot, user_id, CHANNEL_1)
    sub2 = await is_subscribed(context.bot, user_id, CHANNEL_2)

    if not (sub1 and sub2):
        await update.message.reply_text(
            "Чтобы открыть доступ к раскладам, нужна подписка на оба канала 👇",
            reply_markup=subscribe_keyboard(),
        )
        await update.message.reply_text(
            "После подписки нажми «✅ Проверить подписку».",
            reply_markup=MAIN_MENU,
        )
        return ConversationHandler.END

    used_today = get_today_count(user_id)
    if used_today >= DAILY_LIMIT:
        await update.message.reply_text(
            f"Лимит на сегодня исчерпан 🔒\n"
            f"Можно сделать максимум {DAILY_LIMIT} расклада в сутки (UTC).\n\n"
            "Приходи завтра 🌙",
            reply_markup=MAIN_MENU,
        )
        return ConversationHandler.END

    # Засчитываем попытку на старте расклада
    inc_today_count(user_id)

    reply_keyboard = [
        ["Отношения", "Деньги и работа"],
        ["Самореализация", "Другое"],
    ]

    await update.message.reply_text(
        "Колода уже перетасована и ждёт запроса 🔮\n\n"
        "Чтобы расклад подсветил то, что важно, нужно выбрать направление взгляда.\n"
        "Какая сфера жизни сейчас в фокусе?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return SELECT_TOPIC


async def reading_set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь выбрал сферу."""
    topic = update.message.text.strip()
    context.user_data["topic"] = topic

    await update.message.reply_text(
        "Теперь словами.\n"
        "Опиши свой запрос или ситуацию в одном-двух абзацах: что происходит внутри и снаружи, "
        "какой поворот волнует сильнее всего.\n\n"
        "Можно писать свободно — как в личном дневнике.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ENTER_QUESTION


async def reading_set_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получили вопрос, готовим 3 карты и предлагаем тянуть первую."""
    question = update.message.text.strip()
    context.user_data["question"] = question

    cards = random.sample(TAROT_DECK, 3)
    context.user_data["cards"] = cards
    context.user_data["cards_drawn"] = 0

    await update.message.reply_text(
        "Запрос принят. Колода настроилась на тему расклада 🌙\n\n"
        f"Когда почувствуется, что момент подошёл — можно вытянуть первую карту через «{BTN_DRAW_FIRST}».",
        reply_markup=build_draw_keyboard(cards_drawn=0),
    )
    return DRAWING


async def reading_drawing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Логика вытягивания карт и финального разбора."""
    text = update.message.text.strip()
    cards = context.user_data.get("cards", [])
    cards_drawn = context.user_data.get("cards_drawn", 0)
    topic = context.user_data.get("topic", "Не указана")
    question = context.user_data.get("question", "")

    # Завершить расклад
    if text == BTN_CANCEL:
        context.user_data.pop("cards", None)
        context.user_data.pop("cards_drawn", None)
        context.user_data.pop("topic", None)
        context.user_data.pop("question", None)

        await update.message.reply_text(
            "Сеанс остановлен. В любой момент можно вернуться к раскладам через «🔮 Новый расклад».",
            reply_markup=MAIN_MENU,
        )
        return ConversationHandler.END

    # Тянем карту
    if text in {BTN_DRAW_FIRST, BTN_DRAW_SECOND, BTN_DRAW_THIRD} and cards_drawn < 3:
        card_index = cards_drawn
        card = cards[card_index]
        position = card_index + 1

        await update.message.reply_text(
            "Колода перемешивается… 🔄",
            reply_markup=build_draw_keyboard(cards_drawn),
        )
        await asyncio.sleep(5)

        caption = f"{position}️⃣ {card['name']}"
        try:
            with open(card["image"], "rb") as photo:
                await update.message.reply_photo(photo=photo, caption=caption)
        except FileNotFoundError:
            await update.message.reply_text(
                f"{caption}\n(картинка не найдена: {card['image']})"
            )

        await update.message.reply_text("Смотрим, что шепчет эта карта… 🔮")

        explanation = generate_ai_single_card(topic, question, card, position)
        cards_drawn += 1
        context.user_data["cards_drawn"] = cards_drawn

        await update.message.reply_text(
            explanation,
            reply_markup=build_draw_keyboard(cards_drawn),
        )
        return DRAWING

    # Итоговый разбор
    if text == BTN_FULL_READING and cards_drawn == 3:
        await update.message.reply_text(
            "Три голоса колоды собраны вместе. Формирую общий разбор… 💫"
        )
        full_reading = generate_ai_full_reading(topic, question, cards)

        context.user_data.pop("cards", None)
        context.user_data.pop("cards_drawn", None)
        context.user_data.pop("topic", None)
        context.user_data.pop("question", None)

        await update.message.reply_text(
            full_reading,
            reply_markup=MAIN_MENU,
        )
        return ConversationHandler.END

    # Любой другой текст во время расклада
    await update.message.reply_text(
        "Сейчас лучше опираться на кнопки под полем ввода — так расклад будет идти по шагам 😊",
        reply_markup=build_draw_keyboard(cards_drawn),
    )
    return DRAWING


async def reading_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена расклада."""
    context.user_data.pop("cards", None)
    context.user_data.pop("cards_drawn", None)
    context.user_data.pop("topic", None)
    context.user_data.pop("question", None)

    await update.message.reply_text(
        "Сеанс остановлен. Если захочется продолжить позже — «🔮 Новый расклад» всегда под рукой.",
        reply_markup=MAIN_MENU,
    )
    return ConversationHandler.END


# ================== MAIN ==================


def main():
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в переменных окружения")

    init_db()

    # Запускаем HTTP health-сервер для Render в отдельном потоке
    threading.Thread(target=run_health_server, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("about", about))

    # Кнопка About
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_ABOUT}$"), about))

    # Inline-кнопка проверки подписки
    app.add_handler(CallbackQueryHandler(check_subs_callback, pattern="^check_subs$"))

    # Диалог расклада
    reading_conv = ConversationHandler(
        entry_points=[
            CommandHandler("reading", reading_entry),
            MessageHandler(filters.Regex(f"^{BTN_NEW_READING}$"), reading_entry),
        ],
        states={
            SELECT_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reading_set_topic)
            ],
            ENTER_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reading_set_question)
            ],
            DRAWING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reading_drawing)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", reading_cancel),
            MessageHandler(filters.Regex(f"^{BTN_CANCEL}$"), reading_cancel),
        ],
    )
    app.add_handler(reading_conv)

    print("Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    main()