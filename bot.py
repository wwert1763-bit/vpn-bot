import asyncio
import logging
import sqlite3
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9200899614:AAFCcDLprx6o1MIkDVOPfFOeMA1eMhve2P0"
CRYPTO_BOT_TOKEN = "663855:AAcDzgWR4pqFxBOIryv6mHp69gPeq3bK2p1" # Если не нужен, оставь пустым ""
ADMIN_PASSWORD = "1270204"
DB_NAME = "vpn_bot.db"

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        joined_at TEXT,
        is_admin INTEGER DEFAULT 0
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        vpn_key TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, joined_at) VALUES (?, ?, ?)", 
                   (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def is_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return bool(res and res[0] == 1)

def set_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM purchases")
    total_purchases = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(amount) FROM purchases")
    total_money = cursor.fetchone()[0] or 0
    conn.close()
    return total_users, total_purchases, total_money

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def save_purchase(user_id, amount, vpn_key):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO purchases (user_id, amount, vpn_key, created_at) VALUES (?, ?, ?, ?)",
                   (user_id, amount, vpn_key, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

# --- СОСТОЯНИЯ ---
class AdminStates(StatesGroup):
    waiting_for_password = State()
    waiting_for_broadcast = State()

# --- КЛАВИАТУРЫ ---
def main_menu(user_id):
    kb = [
        [KeyboardButton(text="🛒 Купить VPN")],
        [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="ℹ️ Помощь")]
    ]
    if is_admin(user_id):
        kb.append([KeyboardButton(text="⚙️ Админ-панель")])
    else:
        kb.append([KeyboardButton(text="🔑 Ввести пароль админа")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_menu():
    kb = [
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="👥 Пользователи")],
        [KeyboardButton(text="💰 Покупки")],
        [KeyboardButton(text="📢 Рассылка")],
        [KeyboardButton(text="🔙 Выйти в меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def pay_method_menu(plan):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Крипта (CryptoBot)", callback_data=f"crypto_{plan}")],
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"stars_{plan}")]
    ])
    return kb

# --- БОТ ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_user(message.from_user.id, message.from_user.username or "NoUsername")
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n"
        "Добро пожаловать в NEXUS VPN. Здесь ты можешь купить быстрый и надежный доступ.",
        reply_markup=main_menu(message.from_user.id)
    )

# --- ВХОД В АДМИНКУ ---
@dp.message(F.text == "🔑 Ввести пароль админа")
async def ask_password(message: types.Message, state: FSMContext):
    await message.answer("Введите пароль администратора:")
    await state.set_state(AdminStates.waiting_for_password)

@dp.message(AdminStates.waiting_for_password)
async def check_password(message: types.Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        set_admin(message.from_user.id)
        await message.answer("✅ Пароль верный. Вы вошли в админ-панель.", reply_markup=admin_menu())
    else:
        await message.answer("❌ Неверный пароль.", reply_markup=main_menu(message.from_user.id))
    await state.clear()

# --- АДМИН ПАНЕЛЬ ---
@dp.message(F.text == "⚙️ Админ-панель")
async def open_admin(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("Добро пожаловать в админ-панель:", reply_markup=admin_menu())

@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: types.Message):
    if not is_admin(message.from_user.id): return
    users, purchases, money = get_stats()
    await message.answer(
        f"📈 **Статистика бота**\n\n"
        f"👥 Всего пользователей: {users}\n"
        f"🛒 Всего покупок: {purchases}\n"
        f"💵 Заработано: {money} ₽",
        parse_mode="Markdown"
    )

@dp.message(F.text == "👥 Пользователи")
async def admin_users(message: types.Message):
    if not is_admin(message.from_user.id): return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, joined_at FROM users ORDER BY joined_at DESC LIMIT 10")
    users = cursor.fetchall()
    conn.close()
    text = "👥 **Последние 10 юзеров:**\n\n"
    for u in users:
        text += f"ID: `{u[0]}` | @{u[1]} | {u[2]}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "💰 Покупки")
async def admin_purchases(message: types.Message):
    if not is_admin(message.from_user.id): return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, amount, created_at FROM purchases ORDER BY id DESC LIMIT 10")
    purchases = cursor.fetchall()
    conn.close()
    text = "💰 **Последние 10 покупок:**\n\n"
    if not purchases:
        text += "Пока нет покупок."
    for p in purchases:
        text += f"Юзер `{p[0]}` купил на {p[1]} ₽ ({p[2]})\n"
    await message.answer(text, parse_mode="Markdown")

# --- РАССЫЛКА (ИСПРАВЛЕНО) ---
@dp.message(F.text == "📢 Рассылка")
async def start_broadcast(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.answer("Отправьте текст, фото или видео для рассылки (все получат копию этого сообщения):")
    await state.set_state(AdminStates.waiting_for_broadcast)

@dp.message(AdminStates.waiting_for_broadcast)
async def do_broadcast(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    
    users = get_all_users()
    success = 0
    failed = 0
    sent_msg = await message.answer("🚀 Рассылка запущена, подождите...")
    
    for user_id in users:
        try:
            # Копируем сообщение со всеми медиа
            await message.copy_to(chat_id=user_id)
            success += 1
            await asyncio.sleep(0.05)  # Задержка, чтобы Телеграм не забанил за спам
        except TelegramForbiddenError:
            failed += 1  # Юзер заблокировал бота
        except TelegramBadRequest:
            failed += 1  # Ошибка запроса (например, аккаунт удален)
        except Exception as e:
            logging.error(f"Ошибка при рассылке юзеру {user_id}: {e}")
            failed += 1
            
    await sent_msg.edit_text(f"✅ Рассылка завершена.\n\nУспешно: {success}\nОшибок: {failed}")
    await state.clear()

@dp.message(F.text == "🔙 Выйти в меню")
async def exit_admin(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu(message.from_user.id))

# --- ПОЛЬЗОВАТЕЛЬСКАЯ ЧАСТЬ ---
@dp.message(F.text == "🛒 Купить VPN")
async def buy_vpn(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц - 40 ₽", callback_data="select_1m")],
        [InlineKeyboardButton(text="3 месяца - 100 ₽", callback_data="select_3m")]
    ])
    await message.answer("Выберите тариф для покупки:", reply_markup=kb)

@dp.callback_query(F.data.startswith("select_"))
async def select_payment_method(callback: types.CallbackQuery):
    plan = callback.data.split("_")[1]
    price = 40 if plan == "1m" else 100
    await callback.message.edit_text(
        f"Выбран тариф: {plan} ({price} ₽).\nКак будете оплачивать?",
        reply_markup=pay_method_menu(plan)
    )

# --- ОПЛАТА КРИПТОЙ ---
@dp.callback_query(F.data.startswith("crypto_"))
async def process_crypto(callback: types.CallbackQuery):
    if not CRYPTO_BOT_TOKEN or CRYPTO_BOT_TOKEN == "ВСТАВЬ_ТОКЕН_ОТ_CRYPTOBOT":
        await callback.message.answer("⚠️ Админ не настроил CryptoBot.")
        return

    plan = callback.data.split("_")[1]
    price = 40 if plan == "1m" else 100
    
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    payload = {
        "asset": "USDT",
        "amount": str(price),
        "description": f"VPN подписка на {plan}",
        "payload": f"{callback.from_user.id}_{plan}"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        pay_url = data["result"]["pay_url"]
                        invoice_id = data["result"]["invoice_id"]
                        
                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="💳 Оплатить", url=pay_url)],
                            [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_{invoice_id}_{plan}")]
                        ])
                        await callback.message.edit_text(
                            f"💳 Счет на {price} ₽ создан.\nПосле оплаты нажмите кнопку «Я оплатил».",
                            reply_markup=kb
                        )
                    else:
                        await callback.message.answer("❌ Ошибка создания счета.")
                else:
                    await callback.message.answer("❌ Ошибка сети или неверный токен.")
    except Exception as e:
        logging.error(f"CryptoBot Error: {e}")
        await callback.message.answer("❌ Ошибка при обращении к CryptoBot.")

@dp.callback_query(F.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery):
    _, invoice_id, plan = callback.data.split("_")
    
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    payload = {"invoice_ids": [invoice_id]}  # ВАЖНО: массив!
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok") and data["result"]["items"]:
                        invoice = data["result"]["items"][0]
                        
                        if invoice["status"] == "paid":
                            price = 40 if plan == "1m" else 100
                            fake_key = "vless://real-key-from-server@de27.h1cloud.net:25054?...#Germany"
                            save_purchase(callback.from_user.id, price, fake_key)
                            
                            await callback.message.edit_text(
                                f"✅ Оплата подтверждена!\n\nВаш ключ:\n`{fake_key}`\n\nСкопируйте его и вставьте в Happ.",
                                parse_mode="Markdown"
                            )
                        else:
                            await callback.answer("❌ Оплата еще не поступила. Подождите.", show_alert=True)
    except Exception as e:
        logging.error(f"CryptoBot Check Error: {e}")
        await callback.answer("❌ Ошибка проверки оплаты.", show_alert=True)

# --- ОПЛАТА ЗВЕЗДАМИ ---
@dp.callback_query(F.data.startswith("stars_"))
async def process_stars(callback: types.CallbackQuery):
    plan = callback.data.split("_")[1]
    price_rub = 40 if plan == "1m" else 100
    stars_price = price_rub 
    
    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"NEXUS VPN - {plan}",
            description=f"Доступ к VPN на {plan}",
            payload=f"stars_{callback.from_user.id}_{plan}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=f"VPN {plan}", amount=stars_price)]
        )
        await callback.answer()
    except Exception as e:
        logging.error(f"Stars Error: {e}")
        await callback.message.answer("❌ Ошибка выставления счета звездами.")

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("stars_"):
        _, user_id, plan = payload.split("_")
        price = 40 if plan == "1m" else 100
        fake_key = "vless://real-key-from-server@de27.h1cloud.net:25054?...#Germany"
        
        save_purchase(message.from_user.id, price, fake_key)
        
        await message.answer(
            f"✅ Оплата звездами прошла!\n\nВаш ключ:\n`{fake_key}`\n\nСкопируйте его и вставьте в Happ.",
            parse_mode="Markdown"
        )

@dp.message(F.text == "👤 Мой профиль")
async def profile(message: types.Message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM purchases WHERE user_id = ?", (message.from_user.id,))
    count = cursor.fetchone()[0]
    conn.close()
    await message.answer(
        f"👤 Ваш профиль:\nID: `{message.from_user.id}`\nКуплено подписок: {count}",
        parse_mode="Markdown"
    )

# --- ЗАПУСК ---
async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
