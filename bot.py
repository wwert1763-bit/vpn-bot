import asyncio
import logging
import random
import os
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "9200899614:AAFCcDLprx6o1MIkDVOPfFOeMA1eMhve2P0" 
ADMIN_ID = 5884767841 
SUPPORT_USERNAME = "neeloq"

# ВСТАВЬ НОВЫЙ ТОКЕН ОТ CRYPTOBOT
CRYPTO_PAY_TOKEN = "663855:AAcDzgWR4pqFxBOIryv6mHp69gPeq3bK2p1"

# Списки серверов и прокси
VPN_SERVERS = [
    "vless://d65cc14c-f53f-4fe2-b262-97856601319c@169.40.42.75:443?security=reality&pbk=e2RLf57Li_-MDZGE9ss1BWPgP54mqRb5PfXhW2jcVVg&sid=c39cc7310a&sni=yahoo.com&fp=firefox&type=tcp#Germany",
    "vless://b8794f67-80d9-4124-8fc5-2d2ce5516573@50.7.41.142:443?security=reality&pbk=AYL1z7PNyo6LqYLeZpXa50FnK9eEu7o18KHRhOlST1w&sid=bd72&sni=deepl.com&fp=chrome&type=tcp#Switzerland",
    "vless://f8c8dc3d-0d37-46b0-8b34-a7232882fcfe@169.197.142.22:18000?encryption=none&type=tcp&security=none#USA",
    "vless://9a0e84f8-4b58-477f-99da-5fac5a2e58e8@45.133.151.187:443?security=reality&pbk=pAgrBKJCmuSJHIzYkEJTqsOBOVBK_DMtEqFPo-PaTkg&sid=b3c9d0c6bdd114a6&sni=36a466g.fi1.h1clayd.click&fp=ios&type=tcp&headerType=none#Russia"
]

PROXY_LINKS = [
    "https://t.me/proxy?server=kostyanchekloh.lol&port=443&secret=ee3f72634c46d320aaa30d8bb2682e9b497975672d6c696e6b2e7275",
    "https://t.me/proxy?server=fresh.t-proxy.info.&port=25565&secret=ee104462821249bd7ac519130220c25d0963646e2e79656b74616e65742e636f6d",
    "https://t.me/proxy?server=s01.neo-trading.org&port=443&secret=ee7391242569590e01416101927d38b565646e732d73686f702e7275"
]

# Тарифы VPN
VPN_TARIFFS = {
    "vpn_1m": {"name": "VPN 1 месяц", "price_stars": 50, "price_rub": 90, "price_usd": 1},
    "vpn_3m": {"name": "VPN 3 месяца", "price_stars": 150, "price_rub": 270, "price_usd": 3},
    "vpn_7m": {"name": "VPN 7 месяцев", "price_stars": 350, "price_rub": 630, "price_usd": 7}
}

# Тарифы Прокси (19, 10, 7 рублей)
PROXY_TARIFFS = {
    "proxy_1": {"name": "Прокси (19₽)", "price_stars": 15, "price_rub": 19, "price_usd": 0.25},
    "proxy_2": {"name": "Прокси (10₽)", "price_stars": 8, "price_rub": 10, "price_usd": 0.15},
    "proxy_3": {"name": "Прокси (7₽)", "price_stars": 6, "price_rub": 7, "price_usd": 0.10}
}
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def create_crypto_invoice(amount_usd, description, payload):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    payload_data = {
        "currency_type": "fiat", "fiat": "USD", "amount": str(amount_usd),
        "description": description, "payload": payload
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload_data, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("ok"):
                    return data["result"]["bot_invoice_url"]
            return None

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🛡 VPN (полный доступ)", callback_data="menu_vpn")
    builder.button(text="✈️ Прокси (только Telegram)", callback_data="menu_proxy")
    builder.button(text="💬 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME}")
    builder.adjust(1)
    return builder.as_markup()

def tariffs_menu(product_type):
    builder = InlineKeyboardBuilder()
    tariffs = VPN_TARIFFS if product_type == "vpn" else PROXY_TARIFFS
    for key, data in tariffs.items():
        builder.button(text=f"{data['name']} - {data['price_rub']}₽", callback_data=f"tariff_{key}")
    builder.button(text="⬅️ Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def pay_method_menu(tariff_id):
    tariff = VPN_TARIFFS.get(tariff_id) or PROXY_TARIFFS.get(tariff_id)
    builder = InlineKeyboardBuilder()
    builder.button(text=f"⭐ Оплатить Звездами ({tariff['price_stars']})", callback_data=f"stars_{tariff_id}")
    builder.button(text=f"🪙 Оплатить Криптой ({tariff['price_usd']}$)", callback_data=f"crypto_{tariff_id}")
    builder.button(text="⬅️ Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Что хотите приобрести?", reply_markup=main_menu())

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(call: types.CallbackQuery):
    await call.message.edit_text("👋 Привет! Что хотите приобрести?", reply_markup=main_menu())

@dp.callback_query(F.data == "menu_vpn")
async def show_vpn(call: types.CallbackQuery):
    await call.message.edit_text("🛡 Выберите тариф VPN:", reply_markup=tariffs_menu("vpn"))

@dp.callback_query(F.data == "menu_proxy")
async def show_proxy(call: types.CallbackQuery):
    await call.message.edit_text("✈️ Выберите тариф Прокси:", reply_markup=tariffs_menu("proxy"))

@dp.callback_query(F.data.startswith("tariff_"))
async def select_tariff(call: types.CallbackQuery):
    tariff_id = call.data.split("tariff_")[1]
    t = VPN_TARIFFS.get(tariff_id) or PROXY_TARIFFS.get(tariff_id)
    await call.message.edit_text(
        f"Выбран тариф: <b>{t['name']}</b>\nСумма: {t['price_rub']}₽ ({t['price_usd']}$)\n\nКак будем оплачивать?",
        reply_markup=pay_method_menu(tariff_id), parse_mode="HTML"
    )

async def deliver_product(user_id, tariff_id):
    if tariff_id.startswith("vpn"):
        link = random.choice(VPN_SERVERS)
        text = f"✅ Ваш VPN ключ:\n<code>{link}</code>\n\nСкопируйте в Happ."
    else:
        link = random.choice(PROXY_LINKS)
        text = f"✅ Ваша ссылка на прокси:\n<code>{link}</code>\n\nНажмите и подключитесь в Telegram."
    await bot.send_message(user_id, text, parse_mode="HTML")

@dp.callback_query(F.data.startswith("stars_"))
async def pay_stars(call: types.CallbackQuery):
    tariff_id = call.data.split("stars_")[1]
    t = VPN_TARIFFS.get(tariff_id) or PROXY_TARIFFS.get(tariff_id)
    await call.message.answer_invoice(
        title=t['name'], description="Доступ к сервису",
        payload=f"stars_{tariff_id}_{call.from_user.id}",
        currency="XTR", prices=[LabeledPrice(label="XTR", amount=t["price_stars"])],
    )
    await call.answer()

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def on_success_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    parts = payload.split("_")
    tariff_id = "_".join(parts[1:-1])
    await message.answer("✅ Оплата Stars прошла успешно!")
    await deliver_product(message.from_user.id, tariff_id)

@dp.callback_query(F.data.startswith("crypto_"))
async def pay_crypto(call: types.CallbackQuery):
    tariff_id = call.data.split("crypto_")[1]
    t = VPN_TARIFFS.get(tariff_id) or PROXY_TARIFFS.get(tariff_id)
    await call.message.edit_text("⏳ Создаю счет...")
    invoice_url = await create_crypto_invoice(t['price_usd'], t['name'], f"{tariff_id}_{call.from_user.id}")
    if invoice_url:
        builder = InlineKeyboardBuilder()
        builder.button(text=f"💳 Оплатить {t['price_usd']}$", url=invoice_url)
        builder.button(text="⬅️ Назад", callback_data="back_to_main")
        builder.adjust(1)
        await call.message.edit_text(
            f"🪙 <b>Оплата криптой</b>\n\nТариф: {t['name']}\nСумма: {t['price_usd']}$",
            reply_markup=builder.as_markup(), parse_mode="HTML"
        )
    else:
        await call.message.edit_text("❌ Ошибка создания счета. Проверьте токен.")

async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def handle_crypto_webhook(request):
    try:
        data = await request.json()
        if data.get("update_type") == "invoice_paid":
            payload = data["payload"]["payload"]
            user_id = int(payload.split("_")[-1])
            tariff_id = "_".join(payload.split("_")[:-1])
            await deliver_product(user_id, tariff_id)
            return web.Response(text="OK")
    except Exception as e:
        logging.error(f"Webhook error: {e}")
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.router.add_post('/crypto_webhook', handle_crypto_webhook)
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
