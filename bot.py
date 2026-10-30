import asyncio
import logging
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "9200899614:AAFCcDLprx6o1MIkDVOPfFOeMA1eMhve2P0"
ADMIN_ID = 5884767841  # Твой Telegram ID (узнай у @userinfobot)

# Данные сервера Нидерланды
SERVER_IP = "1.1.1.1" 
PUBLIC_KEY = "R1oKq7DaLzXw9P0mNc3bVh5jY2sT8uFg4eWx6AqB1Ck" 
SHORT_ID = "1a2b3c4d"
SNI = "www.microsoft.com"

# Тарифы (price_stars - курс звезд, price_rub - рубли для крипты)
TARIFFS = {
    "1m": {"name": "1 месяц", "price_stars": 50, "price_rub": 90, "days": 30},
    "3m": {"name": "3 месяца", "price_stars": 150, "price_rub": 270, "days": 90},
    "7m": {"name": "7 месяцев", "price_stars": 350, "price_rub": 630, "days": 210}
}

CRYPTO_WALLET = "ТВОЙ_АДРЕС_КОШЕЛЬКА_USDT_TRC20"
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def main_menu():
    builder = InlineKeyboardBuilder()
    for key, data in TARIFFS.items():
        builder.button(text=f"{data['name']} - {data['price_rub']}₽", callback_data=f"tariff_{key}")
    builder.adjust(1)
    return builder.as_markup()

def pay_method_menu(tariff_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Оплатить Звездами", callback_data=f"stars_{tariff_id}")
    builder.button(text="🪙 Оплатить Криптой", callback_data=f"crypto_{tariff_id}")
    builder.button(text="⬅️ Назад", callback_data="back")
    builder.adjust(1)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Привет! Это VPN.\n\nВыбери тариф:",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "back")
async def back_to_menu(call: CallbackQuery):
    await call.message.edit_text("Выбери тариф:", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("tariff_"))
async def select_tariff(call: CallbackQuery):
    tariff_id = call.data.split("_")[1]
    await call.message.edit_text(
        f"Выбран тариф: {TARIFFS[tariff_id]['name']}\nКак будем оплачивать?",
        reply_markup=pay_method_menu(tariff_id)
    )

# --- ОПЛАТА ЗВЕЗДАМИ ---
@dp.callback_query(F.data.startswith("stars_"))
async def pay_stars(call: CallbackQuery):
    tariff_id = call.data.split("_")[1]
    price = TARIFFS[tariff_id]["price_stars"]
    
    await call.message.answer_invoice(
        title=f"VPN: {TARIFFS[tariff_id]['name']}",
        description="Доступ к VPN на выбранный период",
        payload=f"stars_{tariff_id}_{call.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="XTR", amount=price)],
    )
    await call.answer()

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def on_success_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    tariff_id = payload.split("_")[1]
    
    # Генерируем ключ
    new_uuid = str(uuid.uuid4())
    link = f"vless://{new_uuid}@{SERVER_IP}:443?security=reality&pbk={PUBLIC_KEY}&sid={SHORT_ID}&sni={SNI}&fp=chrome&type=tcp#VPN_NL"
    
    await message.answer(
        f"✅ Оплата Stars прошла успешно!\n\n"
        f"🔑 <b>Ваш ключ для Happ:</b>\n<code>{link}</code>\n\n"
        f"Скопируйте и добавьте в Happ.",
        parse_mode="HTML"
    )

# --- ОПЛАТА КРИПТОЙ (Ручная проверка) ---
@dp.callback_query(F.data.startswith("crypto_"))
async def pay_crypto(call: CallbackQuery):
    tariff_id = call.data.split("_")[1]
    price = TARIFFS[tariff_id]["price_rub"]
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Я оплатил", callback_data=f"check_crypto_{tariff_id}")
    
    await call.message.edit_text(
        f"🪙 Оплата криптой\n"
        f"Сумма: {price}₽ (в эквиваленте USDT)\n\n"
        f"Адрес кошелька (TRC20):\n<code>{CRYPTO_WALLET}</code>\n\n"
        f"Переведите точную сумму и нажмите кнопку.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("check_crypto_"))
async def check_crypto(call: CallbackQuery):
    tariff_id = call.data.split("_")[1]
    
    await bot.send_message(
        ADMIN_ID,
        f"💰 @{call.from_user.username} нажал 'Оплатил крипту'!\n"
        f"User ID: {call.from_user.id}\n"
        f"Тариф: {TARIFFS[tariff_id]['name']}\n\n"
        f"Если деньги пришли, напиши: /give_key {call.from_user.id} {tariff_id}"
    )
    await call.message.edit_text("⏳ Проверяю оплату... Ожидайте подтверждения от админа.")

@dp.message(Command("give_key"))
async def give_key_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        args = message.text.split()
        target_id = int(args[1])
        tariff_id = args[2]
    except:
        await message.answer("Использование: /give_key <user_id> <tariff_id>")
        return
    
    new_uuid = str(uuid.uuid4())
    link = f"vless://{new_uuid}@{SERVER_IP}:443?security=reality&pbk={PUBLIC_KEY}&sid={SHORT_ID}&sni={SNI}&fp=chrome&type=tcp#VPN_NL"
    
    await bot.send_message(
        target_id,
        f"✅ Ваша подписка активирована!\n\n"
        f"🔑 <b>Ваш ключ для Happ:</b>\n<code>{link}</code>\n\n"
        f"Скопируйте и добавьте в Happ.",
        parse_mode="HTML"
    )
    await message.answer(f"Ключ выдан пользователю {target_id}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
