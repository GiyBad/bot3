import os
import mimetypes
from hydrogram import Client, filters
from hydrogram.types import Message
from aiohttp import web

# --- НАСТРОЙКИ ---
API_ID = 34753668
API_HASH = "71f8cba6061f6a8973720dd52e7ed2bb"
BOT_TOKEN = "8036788093:AAFSlZiU78PMBWX8m3QyHxfiJ9ufaALHhoQ"
CHANNEL_ID = -1002244248474
# Твой URL на Render (без слэша в конце)
BASE_URL = "https://bot3-thub.onrender.com"

# Инициализация клиента Telegram
app = Client("paritube_stream", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- ЛОГИКА БОТА ---
@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    if message.document and not message.document.mime_type.startswith("video/"):
        return await message.reply("❌ Это не видео.")

    msg = await message.reply("⏳ Сохраняю видео в облако PariTube...")
    
    try:
        # Пересылаем в канал
        fwd = await message.forward(CHANNEL_ID)
        
        # Ссылки для сайта
        stream_link = f"{BASE_URL}/stream/{fwd.id}"
        watch_link = f"{BASE_URL}/watch/{fwd.id}"
        
        await msg.edit(
            f"✅ **Готово!**\n\n"
            f"🔗 Ссылка для плеера (src):\n`{stream_link}`\n\n"
            f"📺 Страница просмотра:\n{watch_link}"
        )
    except Exception as e:
        await msg.edit(f"❌ Ошибка: {e}")

# --- ЛОГИКА СТРИМИНГ-СЕРВЕРА ---
async def stream_handler(request):
    msg_id = int(request.match_info['msg_id'])
    
    # Ищем сообщение в канале
    message = await app.get_messages(CHANNEL_ID, msg_id)
    
    if not message or not (message.video or message.document):
        return web.Response(text="Видео не найдено", status=404)

    media = message.video or message.document
    
    # Настройка заголовков для браузера
    headers = {
        "Content-Type": media.mime_type or "video/mp4",
        "Content-Disposition": f'inline; filename="{media.file_name or "video.mp4"}"',
        "Accept-Ranges": "bytes"
    }

    # Создаем стрим-ответ (потоковая передача данных из ТГ)
    response = web.StreamResponse(status=200, headers=headers)
    await response.prepare(request)

    # Качаем файл кусочками и сразу отдаем в браузер
    async for chunk in app.stream_media(media):
        await response.write(chunk)
    
    return response

# Простая страница просмотра (тестовая)
async def watch_handler(request):
    msg_id = request.match_info['msg_id']
    html = f"""
    <html>
        <body style="background:#000; display:flex; justify-content:center; align-items:center; height:100vh; margin:0;">
            <video controls width="80%" src="{BASE_URL}/stream/{msg_id}"></video>
        </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

# --- ЗАПУСК ---
async def start_server():
    server = web.Application()
    server.add_routes([
        web.get('/stream/{msg_id}', stream_handler),
        web.get('/watch/{msg_id}', watch_handler)
    ])
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("🌍 HTTP Сервер запущен на порту 8080")

async def main():
    await app.start()
    await start_server()
    # Держим бота запущенным
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
