import asyncio
import logging
import random
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "9200899614:AAFCcDLprx6o1MIkDVOPfFOeMA1eMhve2P0" # Вставь свой токен от BotFather
ADMIN_ID = 5884767841 
SUPPORT_USERNAME = "neeloq"

# Список серверов
SERVERS = [
    "vless://d65cc14c-f53f-4fe2-b262-97856601319c@169.40.42.75:443?security=reality&pbk=e2RLf57Li_-MDZGE9ss1BWPgP54mqRb5PfXhW2jcVVg&sid=c39cc7310a&sni=yahoo.com&fp=firefox&type=tcp#Germany",
    "vless://b8794f67-80d9-4124-8fc5-2d2ce5516573@50.7.41.142:443?security=reality&pbk=AYL1z7PNyo6LqYLeZpXa50FnK9eEu7o18KHRhOlST1w&sid=bd72&sni=deepl.com&fp=chrome&type=tcp#Switzerland",
    "vless://f8c8dc3d-0d37-46b0-8b34-a7232882fcfe@169.197.142.22:18000?encryption=none&type=tcp&security=none#USA",
    "vless://9a0e84f8-4b58-477f-99da-5fac5a2e58e8@45.133.151.187:443?security=reality&pbk=pAgrBKJCmuSJHIzYkEJTqsOBOVBK_DMtEqFPo-PaTkg&sid=b3c9d0c6bdd114a6&sni=36a466g.fi1.h1clayd.click&fp=ios&type=tcp&headerType=none#Russia"
]

TARIFFS = {
    "1m": {"name": "1 месяц", "price_stars": 50, "price_rub": 90, "price_usd": 1, "days": 30},
    "3m": {"name": "3 месяца", "price_stars": 150, "price_rub": 270, "price_usd": 3, "days": 90},
    "7m": {"name": "7 месяцев", "price_stars": 350, "price_rub": 630, "price_usd": 7, "days": 210}
}

# Заглушка для кошелька (пока нет автовыдачи)
CRYPTO_WALLET = "TAZnQFAMux1aFLmUQLRyuccTmuvzVxA8FA"
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def main_menu():
    builder = InlineKeyboardBuilder()
    for key, data in TARIFFS.items():
        builder.button(text=f"{data['name']} - {data['price_rub']}₽", callback_data=f"tariff_{key}")
    builder.button(text="📖 Инструкция", callback_data="instruction")
    builder.button(text="💬 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME}")
    builder.adjust(1, 1, 1, 2)
    return builder.as_markup()

def pay_method_menu(tariff_id):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"⭐ Оплатить Звездами ({TARIFFS[tariff_id]['price_stars']})", callback_data=f"stars_{tariff_id}")
    builder.button(text=f"🪙 Оплатить Криптой ({TARIFFS[tariff_id]['price_usd']}$)", callback_data=f"crypto_{tariff_id}")
    builder.button(text="⬅️ Назад", callback_data="back")
    builder.adjust(1)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Это VPN.\n\nВыбери тариф:", reply_markup=main_menu())

@dp.callback_query(F.data == "instruction")
async def show_instruction(call: types.CallbackQuery):
    text = "📖 <b>Как подключиться:</b>\n\n1. Скачайте Happ.\n2. Купите тариф и скопируйте ключ.\n3. В Happ нажмите «+» -> «Импорт из буфера».\n4. Вставьте ключ."
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="back")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "back")
async def back_to_menu(call: types.CallbackQuery):
    await call.message.edit_text("Выбери тариф:", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("tariff_"))
async def select_tariff(call: types.CallbackQuery):
    tariff_id = call.data.split("_")[1]
    t = TARIFFS[tariff_id]
    await call.message.edit_text(
        f"Выбран тариф: <b>{t['name']}</b>\nСумма: {t['price_rub']}₽ ({t['price_usd']}$)\n\nКак будем оплачивать?",
        reply_markup=pay_method_menu(tariff_id),
        parse_mode="HTML"
    )

# --- ОПЛАТА ЗВЕЗДАМИ ---
@dp.callback_query(F.data.startswith("stars_"))
async def pay_stars(call: types.CallbackQuery):
    tariff_id = call.data.split("_")[1]
    price = TARIFFS[tariff_id]["price_stars"]
    await call.message.answer_invoice(
        title=f"VPN: {TARIFFS[tariff_id]['name']}",
        description="Доступ к VPN",
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
    selected_link = random.choice(SERVERS)
    await message.answer(
        f"✅ Оплата Stars прошла успешно!\n\n🔑 <b>Ваш ключ:</b>\n<code>{selected_link}</code>\n\nСкопируйте и добавьте в Happ.",
        parse_mode="HTML"
    )

# --- ОПЛАТА КРИПТОЙ (РУЧНАЯ) ---
@dp.callback_query(F.data.startswith("crypto_"))
async def pay_crypto(call: types.CallbackQuery):
    tariff_id = call.data.split("_")[1]
    price_rub = TARIFFS[tariff_id]["price_rub"]
    price_usd = TARIFFS[tariff_id]["price_usd"]
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Я оплатил", callback_data=f"check_crypto_{tariff_id}")
    builder.button(text="⬅️ Назад", callback_data="back")
    builder.adjust(1)
    
    await call.message.edit_text(
        f"🪙 <b>Оплата криптой</b>\n\n"
        f"Тариф: {TARIFFS[tariff_id]['name']}\n"
        f"Сумма: {price_rub}₽ ({price_usd}$)\n\n"
        f"Адрес кошелька:\n<code>{663855:AAcDzgWR4pqFxBOIryv6mHp69gPeq3bK2p1}</code>\n\n"
        f"Переведите точную сумму и нажмите кнопку.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("check_crypto_"))
async def check_crypto(call: types.CallbackQuery):
    tariff_id = call.data.split("_")[1]
    await bot.send_message(ADMIN_ID, f"💰 @{call.from_user.username} нажал 'Оплатил'!\nID: {call.from_user.id}\nТариф: {TARIFFS[tariff_id]['name']}\n\nЕсли пришли, напиши: /give_key {call.from_user.id} {tariff_id}")
    await call.message.edit_text("⏳ Ожидайте подтверждения от админа.")

@dp.message(Command("give_key"))
async def give_key_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        target_id = int(args[1])
        tariff_id = args[2]
    except:
        await message.answer("Использование: /give_key <user_id> <tariff_id>")
        return
    selected_link = random.choice(SERVERS)
    await bot.send_message(target_id, f"✅ Подписка активирована!\n\n🔑 <b>Ваш ключ:</b>\n<code>{selected_link}</code>", parse_mode="HTML")
    await message.answer(f"Ключ выдан {target_id}")

# --- ВЕБ-СЕРВЕР ДЛЯ ПИНАЛКИ ---
async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def main():
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
