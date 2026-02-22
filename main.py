import os
import asyncio
from hydrogram import Client, filters
from hydrogram.handlers import MessageHandler # Добавили импорт
from hydrogram.types import Message
from aiohttp import web

# --- НАСТРОЙКИ ---
API_ID = 34753668
API_HASH = "71f8cba6061f6a8973720dd52e7ed2bb"
BOT_TOKEN = "8036788093:AAFSlZiU78PMBWX8m3QyHxfiJ9ufaALHhoQ"
CHANNEL_ID = -1002244248474
BASE_URL = "https://bot3-thub.onrender.com"

app = None

# --- ЛОГИКА БОТА ---
async def handle_video(client, message: Message):
    if message.document and not (message.document.mime_type and message.document.mime_type.startswith("video/")):
        return
    
    msg = await message.reply("⏳ Сохраняю видео в облако PariTube...")
    try:
        fwd = await message.forward(CHANNEL_ID)
        stream_link = f"{BASE_URL}/stream/{fwd.id}"
        watch_link = f"{BASE_URL}/watch/{fwd.id}"
        
        await msg.edit(
            f"✅ **Готово!**\n\n"
            f"🔗 Ссылка для плеера (src):\n`{stream_link}`\n\n"
            f"📺 Страница просмотра:\n{watch_link}"
        )
    except Exception as e:
        await msg.edit(f"❌ Ошибка: {e}")

# --- ЛОГИКА СТРИМИНГА ---
async def stream_handler(request):
    try:
        msg_id = int(request.match_info['msg_id'])
        message = await app.get_messages(CHANNEL_ID, msg_id)
        
        if not message or not (message.video or message.document):
            return web.Response(text="Видео не найдено", status=404)

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

async def watch_handler(request):
    msg_id = request.match_info['msg_id']
    html = f'<html><body style="background:#000;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;"><video controls width="80%" src="{BASE_URL}/stream/{msg_id}"></video></body></html>'
    return web.Response(text=html, content_type='text/html')

# --- ЗАПУСК ---
async def main():
    global app
    app = Client(
        "paritube_stream", 
        api_id=API_ID, 
        api_hash=API_HASH, 
        bot_token=BOT_TOKEN,
        in_memory=True
    )
    
    # ИСПРАВЛЕННЫЙ МЕТОД РЕГИСТРАЦИИ ХЕНДЛЕРА
    app.add_handler(MessageHandler(handle_video, filters.video | filters.document))
    
    await app.start()
    print("🤖 Бот запущен...")

    server = web.Application()
    server.add_routes([
        web.get('/stream/{msg_id}', stream_handler),
        web.get('/watch/{msg_id}', watch_handler)
    ])
    
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("🌍 Сервер стриминга запущен на порту 8080")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
