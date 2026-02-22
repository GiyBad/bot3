import asyncio
import aiohttp
from hydrogram import Client, filters
from hydrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- НАСТРОЙКИ ---
API_ID = 34753668
API_HASH = "71f8cba6061f6a8973720dd52e7ed2bb"
BOT_TOKEN = "8036788093:AAFSlZiU78PMBWX8m3QyHxfiJ9ufaALHhoQ"
CHANNEL_ID = -1003691010798
BASE_URL = "https://bot3-thub.onrender.com"
SITE_API = "https://paritube.xo.je/api_upload.php"

# Временное хранилище данных пользователей
user_data = {} 
app = None  # Теперь инициализируем внутри функции

# --- ОБРАБОТЧИКИ (Переносим сюда) ---
async def start_cmd(client, message):
    await message.reply("Привет! Чтобы публиковать видео, настройте профиль:\n1. Пришли свой ID (например: `ID: 1`)\n2. Пришли свои COOKIE (например: `__test=...`)")

async def set_id(client, message):
    uid = message.matches[0].group(1)
    user_data[message.from_user.id] = user_data.get(message.from_user.id, {})
    user_data[message.from_user.id]['site_id'] = uid
    await message.reply(f"✅ ID {uid} сохранен!")

async def set_cookie(client, message):
    cookie = message.text.strip()
    user_data[message.from_user.id] = user_data.get(message.from_user.id, {})
    user_data[message.from_user.id]['cookie'] = cookie
    await message.reply("✅ Cookie сохранены! Присылай видео.")

async def handle_video(client, message):
    user_id = message.from_user.id
    if user_id not in user_data or 'site_id' not in user_data[user_id]:
        await message.reply("❌ Сначала пришли свой ID в формате `ID: 1`")
        return

    msg = await message.reply("⏳ Генерирую прямую ссылку...")
    fwd = await message.forward(CHANNEL_ID)
    stream_link = f"{BASE_URL}/stream/{fwd.id}"
    title = message.caption if message.caption else f"Видео {fwd.id}"

    btn = InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 ОПУБЛИКОВАТЬ НА САЙТЕ", callback_data=f"pub_{fwd.id}")
    ]])
    
    user_data[user_id][f"title_{fwd.id}"] = title
    user_data[user_id][f"url_{fwd.id}"] = stream_link
    await msg.edit(f"✅ Ссылка готова!\n\n**Название:** {title}\n**URL:** {stream_link}", reply_markup=btn)

async def publish_call(client, callback_query):
    fwd_id = callback_query.data.split("_")[1]
    uid = callback_query.from_user.id
    
    if uid not in user_data or 'cookie' not in user_data[uid]:
        await callback_query.answer("❌ Ошибка: Пришли куки __test=... из браузера", show_alert=True)
        return

    data = {
        "key": "pari_secret_777",
        "title": user_data[uid].get(f"title_{fwd_id}"),
        "url": user_data[uid].get(f"url_{fwd_id}"),
        "user_id": user_data[uid]['site_id']
    }

    headers = {
        "Cookie": user_data[uid]['cookie'],
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(SITE_API, data=data, headers=headers, timeout=10) as resp:
                res_text = await resp.text()
                if "OK" in res_text:
                    await callback_query.message.edit(f"🎉 **ОПУБЛИКОВАНО!**\nСмотреть: https://paritube.xo.je")
                else:
                    await callback_query.answer(f"❌ Ошибка хостинга: {res_text[:50]}", show_alert=True)
        except Exception as e:
            await callback_query.answer(f"❌ Тайм-аут или ошибка сети", show_alert=True)

# --- СЕРВЕР СТРИМИНГА ---
async def stream_handler(request):
    try:
        msg_id = int(request.match_info['msg_id'])
        msg = await app.get_messages(CHANNEL_ID, msg_id)
        media = msg.video or msg.document
        response = web.StreamResponse(status=200, headers={"Content-Type": "video/mp4"})
        await response.prepare(request)
        async for chunk in app.stream_media(media): await response.write(chunk)
        return response
    except: return web.Response(status=404)

# --- ЗАПУСК ---
async def run_bot():
    global app
    # Создаем клиент ВНУТРИ цикла
    app = Client("paritube_full", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
    
    # Регистрируем хендлеры вручную
    app.add_handler(hydrogram.handlers.MessageHandler(start_cmd, filters.command("start")))
    app.add_handler(hydrogram.handlers.MessageHandler(set_id, filters.regex(r"ID: (\d+)")))
    app.add_handler(hydrogram.handlers.MessageHandler(set_cookie, filters.regex(r"__test=(.*)")))
    app.add_handler(hydrogram.handlers.MessageHandler(handle_video, filters.video | filters.document))
    app.add_handler(hydrogram.handlers.CallbackQueryHandler(publish_call, filters.regex(r"pub_(\d+)")))
    
    import hydrogram.handlers # Чтобы работало добавление выше
    
    await app.start()
    
    server = web.Application()
    server.add_routes([web.get('/stream/{msg_id}', stream_handler)])
    runner = web.AppRunner(server)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8080).start()
    
    print("🚀 Бот запущен на Render!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    import hydrogram.handlers
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        pass
