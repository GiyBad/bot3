import os
import asyncio
import aiohttp
from hydrogram import Client, filters
from hydrogram.handlers import MessageHandler
from hydrogram.types import Message
from aiohttp import web

# --- НАСТРОЙКИ ---
API_ID = 34753668
API_HASH = "71f8cba6061f6a8973720dd52e7ed2bb"
BOT_TOKEN = "8036788093:AAFSlZiU78PMBWX8m3QyHxfiJ9ufaALHhoQ"
CHANNEL_ID = -1003691010798
BASE_URL = "https://bot3-thub.onrender.com"

# Настройки твоего сайта
PHP_API_URL = "https://paritube.xo.je/api_upload.php"
SECRET_KEY = "pari_secret_777"

app = None

# --- ЛОГИКА БОТА + АВТО-ЗАГРУЗКА ---
async def handle_video(client, message: Message):
    if message.document and not (message.document.mime_type and message.document.mime_type.startswith("video/")):
        return
    
    msg = await message.reply("🚀 Загружаю видео в PariTube Cloud...")
    try:
        # 1. Пересылаем в канал
        fwd = await message.forward(CHANNEL_ID)
        stream_link = f"{BASE_URL}/stream/{fwd.id}"
        
        # Название берем из описания к видео (caption) или ставим дефолт
        title = message.caption if message.caption else f"Видео #{fwd.id}"

        # 2. АВТО-ОТПРАВКА НА САЙТ
        async with aiohttp.ClientSession() as session:
            payload = {
                "key": SECRET_KEY,
                "title": title,
                "url": stream_link
            }
            async with session.post(PHP_API_URL, data=payload) as resp:
                api_result = await resp.text()

        if api_result.strip() == "OK":
            await msg.edit(f"✅ **ОПУБЛИКОВАНО!**\n\n🔗 Ссылка: {stream_link}\n📺 Проверить: https://paritube.xo.je")
        else:
            await msg.edit(f"⚠️ Сохранено в облако, но сайт вернул ошибку: {api_result}")

    except Exception as e:
        await msg.edit(f"❌ Ошибка загрузки: {e}")

# --- ЛОГИКА СТРИМИНГА ---
async def stream_handler(request):
    try:
        msg_id = int(request.match_info['msg_id'])
        message = await app.get_messages(CHANNEL_ID, msg_id)
        if not message or not (message.video or message.document):
            return web.Response(text="Файл не найден", status=404)

        media = message.video or message.document
        headers = {
            "Content-Type": media.mime_type or "video/mp4",
            "Content-Disposition": f'inline; filename="{media.file_name or "video.mp4"}"',
            "Accept-Ranges": "bytes"
        }
        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)
        async for chunk in app.stream_media(media):
            await response.write(chunk)
        return response
    except Exception as e:
        return web.Response(text=str(e), status=500)

# --- ЗАПУСК ---
async def main():
    global app
    app = Client("paritube_stream", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
    app.add_handler(MessageHandler(handle_video, filters.video | filters.document))
    
    await app.start()
    
    server = web.Application()
    server.add_routes([web.get('/stream/{msg_id}', stream_handler)])
    
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    
    print("🚀 PariTube Система запущена!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
