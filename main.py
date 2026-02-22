import os
import asyncio
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

# Очередь для хранения видео, пока сайт их не заберет
video_queue = []

app = None

# --- ОБРАБОТКА ВИДЕО ---
async def handle_video(client, message: Message):
    global video_queue
    
    # Проверка: видео или документ-видео
    if message.document and not (message.document.mime_type and message.document.mime_type.startswith("video/")):
        return
    
    msg = await message.reply("🚀 Видео получено! Оно появится на сайте через пару секунд...")
    
    try:
        # 1. Пересылаем в канал
        fwd = await message.forward(CHANNEL_ID)
        stream_link = f"{BASE_URL}/stream/{fwd.id}"
        
        # Название из подписи
        title = message.caption if message.caption else f"Новое видео #{fwd.id}"

        # 2. Добавляем в очередь (сайт заберет это сам)
        video_queue.append({
            "title": title,
            "url": stream_link
        })
        
        await msg.edit(f"✅ **ГОТОВО!**\n🔗 Ссылка: {stream_link}\n\nПросто открой главную страницу сайта, чтобы видео сохранилось.")

    except Exception as e:
        await msg.edit(f"❌ Ошибка бота: {e}")

# --- API ДЛЯ САЙТА ---
async def stream_handler(request):
    try:
        msg_id = int(request.match_info['msg_id'])
        message = await app.get_messages(CHANNEL_ID, msg_id)
        if not message or not (message.video or message.document):
            return web.Response(text="Файл не найден", status=404)

        media = message.video or message.document
        headers = {
            "Content-Type": media.mime_type or "video/mp4",
            "Accept-Ranges": "bytes"
        }
        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)
        async for chunk in app.stream_media(media):
            await response.write(chunk)
        return response
    except Exception as e:
        return web.Response(text=str(e), status=500)

async def get_queue_handler(request):
    global video_queue
    # Разрешаем сайту обращаться к боту (CORS)
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json"
    }
    if not video_queue:
        return web.json_response({"status": "empty"}, headers=headers)
    
    # Отдаем данные и удаляем из очереди
    data = video_queue.pop(0)
    return web.json_response(data, headers=headers)

# --- ЗАПУСК ---
async def main():
    global app
    app = Client("paritube_stream", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
    app.add_handler(MessageHandler(handle_video, filters.video | filters.document))
    
    await app.start()
    
    server = web.Application()
    server.add_routes([
        web.get('/stream/{msg_id}', stream_handler),
        web.get('/get_new_video', get_queue_handler) # Эндпоинт для сайта
    ])
    
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    
    print("🚀 PariTube Bot + API Server Started!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
