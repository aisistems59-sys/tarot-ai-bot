import os
import asyncio
import random
from typing import List, Dict

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    LabeledPrice,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from openai import OpenAI

# ================= НАСТРОЙКИ ===================

# 👉 Токен бота и ключ OpenAI теперь берём из переменных окружения
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 👉 НАСТРОЙКА ЦЕНЫ (сколько звёзд за 1 расклад)
STARS_PER_READING = 50

# 👉 ПЕЙЛОАД ДЛЯ ИНВОЙСА (идентификатор товара)
INVOICE_PAYLOAD = "tarot_full_reading_50stars"

# 👉 ПРОМОКОДЫ: "КОД": сколько раскладов даёт
PROMO_CODES: Dict[str, int] = {
    "ARCANA7QF3": 1,
    "MOON9ZK42": 1,
    "STAR5VQ81": 1,
    "TAROT3LX9": 1,
    "MYSTIC8PZ4": 1,
    "NIGHT2RQ7": 1,
    "CARDS6WF1": 1,
    "TRIDENT4KJ": 1,
    "PORTAL7XS3": 1,
    "SHADOW9LT2": 1,
    "AURA5DN38": 1,
    "SIGIL3HV6": 1,
    "RITUAL8QW1": 1,
    "ARCANUM4BZ7": 1,
    "VEIL2KM95": 1,
    "ORACLE7JP3": 1,
    "RUNE6CZ41": 1,
    "SPIRIT9FT2": 1,
    "CANDLE5YX8": 1,
    "KEY3VR72": 1,
    "PATH8QL39": 1,
    "MIRROR4SW6": 1,
    "GATE7HN25": 1,
    "FATE9KU13": 1,
    "OMEN6PJ84": 1,
    "SIGN3XZ57": 1,
    "THREAD8MV2": 1,
    "KNOT5JD61": 1,
    "CIRCLE7QA9": 1,
    "ALTAR2FW8": 1,
}

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
SELECT_TOPIC, ENTER_QUESTION, DRAWING, ENTER_PROMO = range(4)

# ====== ТЕКСТЫ КНОПОК ======
BTN_NEW_READING = "🔮 Новый расклад"
BTN_ENTER_PROMO = "🎟 Ввести промокод"
BTN_BUY_READING = "💫 Купить расклад за 50⭐"
BTN_BALANCE = "💰 Мой баланс"
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
        [BTN_ENTER_PROMO, BTN_BUY_READING],
        [BTN_BALANCE, BTN_ABOUT],
    ],
    resize_keyboard=True,
)

# ================== ПРОСТОЙ HTTP-СЕРВЕР ДЛЯ RENDER ==================


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Простейший ответ для проверки Render'ом
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK")


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


def generate_ai_single_card(topic: str, question: str, card: Dict[str, str], position: int) -> str:
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
        "Здесь колода говорит языком символов, а нейросеть помогает собрать всё в понятные смыслы 🌙\n\n"
        "Формат простой:\n"
        "• три карты, которые вытягиваются по очереди,\n"
        "• разбор каждой карты в контексте твоего запроса,\n"
        "• общий вывод и мягкие рекомендации о следующих шагах.\n\n"
        f"Один полный расклад стоит {STARS_PER_READING}⭐ или открывается по промокоду.\n\n"
        "Можно:\n"
        f"• открыть доступ к сеансам — «{BTN_BUY_READING}» или «{BTN_ENTER_PROMO}»,\n"
        f"• посмотреть, сколько раскладов уже есть на балансе — «{BTN_BALANCE}»,\n"
        f"• сразу перейти к картам — «{BTN_NEW_READING}».",
        reply_markup=MAIN_MENU,
    )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """О боте"""
    await update.message.reply_text(
        "«Тройка Арканов» — это бот-таролог на базе нейросети 🔮\n\n"
        "Цель раскладов — не напугать и не дать приговор, а подсветить ситуацию под другим углом:\n"
        "• помочь уловить внутреннее состояние,\n"
        "• увидеть скрытые мотивы и желания,\n"
        "• наметить мягкие, но реальные шаги вперёд.\n\n"
        "Сначала открывается доступ к раскладам (Stars или промокод), а потом:\n"
        f"1) запускается «{BTN_NEW_READING}»,\n"
        "2) вытягиваются три карты по одной,\n"
        "3) в финале собирается общий разбор.",
        reply_markup=MAIN_MENU,
    )


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать баланс раскладов пользователя."""
    credits = context.user_data.get("credits", 0)

    if credits > 0:
        text = (
            f"Сейчас на балансе {credits} полн"
            f"{'' if credits == 1 else 'ых'} расклад"
            f"{'' if credits == 1 else 'а'} 🔮\n\n"
            f"В любой момент можно запустить новый сеанс через «{BTN_NEW_READING}»."
        )
    else:
        text = (
            "Пока на балансе нет доступных раскладов.\n\n"
            "Получить сеанс можно так:\n"
            f"• активировать промокод — «{BTN_ENTER_PROMO}»,\n"
            f"• купить расклад за {STARS_PER_READING}⭐ — «{BTN_BUY_READING}»."
        )

    await update.message.reply_text(text, reply_markup=MAIN_MENU)

# ---------- ПРОМОКОДЫ ----------


async def promo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало ввода промокода."""
    await update.message.reply_text(
        "Введи промокод одним сообщением.\n\n"
        "Например: ARCANA7QF3\n\n"
        "Для отмены всегда можно написать /cancel.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ENTER_PROMO


async def promo_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверяем промокод."""
    code_raw = update.message.text.strip()
    code = code_raw.upper()

    used_codes = context.user_data.get("used_promos", [])
    balance = context.user_data.get("credits", 0)

    if code in used_codes:
        await update.message.reply_text(
            "Этот промокод уже был использован. Для нового сеанса понадобится другой код.",
            reply_markup=MAIN_MENU,
        )
        return ConversationHandler.END

    if code not in PROMO_CODES:
        await update.message.reply_text(
            "Колода промокодов молчит на этот набор символов.\n"
            "Стоит проверить написание или запросить другой код.",
            reply_markup=MAIN_MENU,
        )
        return ConversationHandler.END

    plus = PROMO_CODES[code]
    balance += plus
    used_codes.append(code)

    context.user_data["credits"] = balance
    context.user_data["used_promos"] = used_codes

    await update.message.reply_text(
        "Промокод принят 🔑\n"
        f"На баланс добавлено сеансов: {plus}\n"
        f"Текущее количество доступных раскладов: {balance}.\n\n"
        f"Когда внутри появится запрос — можно запускать «{BTN_NEW_READING}».",
        reply_markup=MAIN_MENU,
    )
    return ConversationHandler.END


async def promo_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ввод промокода прерван. Если понадобится — можно вернуться к этому позже.",
        reply_markup=MAIN_MENU,
    )
    return ConversationHandler.END

# ---------- ОПЛАТА STARS ----------


async def buy_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляем инвойс на покупку расклада за Stars."""
    chat_id = update.effective_chat.id

    prices = [LabeledPrice(label="Полный расклад из трёх карт", amount=STARS_PER_READING)]

    await context.bot.send_invoice(
        chat_id=chat_id,
        title="Полный расклад Таро 🔮",
        description="Три карты, разбор каждой и общий вывод по раскладу.",
        payload=INVOICE_PAYLOAD,
        provider_token="",  # для Telegram Stars можно оставить пустым
        currency="XTR",     # XTR = Telegram Stars
        prices=prices,
        max_tip_amount=0,
        need_name=False,
        need_email=False,
        need_phone_number=False,
        is_flexible=False,
    )


async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждаем pre_checkout для Stars."""
    query = update.pre_checkout_query

    if query.invoice_payload != INVOICE_PAYLOAD:
        await query.answer(ok=False, error_message="Что-то пошло не так с оплатой.")
    else:
        await query.answer(ok=True)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """После успешной оплаты начисляем 1 расклад."""
    payment = update.message.successful_payment

    if payment.invoice_payload != INVOICE_PAYLOAD:
        return

    credits = context.user_data.get("credits", 0) + 1
    context.user_data["credits"] = credits

    await update.message.reply_text(
        "Оплата прошла успешно ✨\n"
        "На баланс добавлен один полный расклад.\n"
        f"Сейчас доступно сеансов: {credits}.\n\n"
        f"Когда придёт время — можно запускать «{BTN_NEW_READING}».",
        reply_markup=MAIN_MENU,
    )

# ---------- ЛОГИКА РАСКЛАДА ----------


async def reading_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт расклада – проверяем наличие слотов и выбираем сферу."""
    credits = context.user_data.get("credits", 0)

    if credits <= 0:
        await update.message.reply_text(
            "Похоже, доступных раскладов пока нет.\n\n"
            "Можно:\n"
            f"• активировать промокод — «{BTN_ENTER_PROMO}»,\n"
            f"• приобрести сеанс за {STARS_PER_READING}⭐ — «{BTN_BUY_READING}».",
            reply_markup=MAIN_MENU,
        )
        return ConversationHandler.END

    # списываем один расклад сразу при старте
    context.user_data["credits"] = credits - 1

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

    # Запускаем HTTP health-сервер для Render в отдельном потоке
    threading.Thread(target=run_health_server, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("balance", show_balance))

    # Баланс и инфо по кнопкам
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_BALANCE}$"), show_balance))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_ABOUT}$"), about))

    # Покупка расклада
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_BUY_READING}$"), buy_reading))
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler)
    )

    # Диалог промокода
    promo_conv = ConversationHandler(
        entry_points=[
            CommandHandler("promo", promo_start),
            MessageHandler(filters.Regex(f"^{BTN_ENTER_PROMO}$"), promo_start),
        ],
        states={
            ENTER_PROMO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, promo_apply)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", promo_cancel),
        ],
    )
    app.add_handler(promo_conv)

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