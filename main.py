import asyncio
from hydrogram import Client, filters
from hydrogram.types import Message
from aiohttp import web

# --- НАСТРОЙКИ ---
API_ID = 34753668
API_HASH = "71f8cba6061f6a8973720dd52e7ed2bb"
BOT_TOKEN = "8036788093:AAFSlZiU78PMBWX8m3QyHxfiJ9ufaALHhoQ"
CHANNEL_ID = -1003691010798
BASE_URL = "https://bot3-thub.onrender.com"

video_queue = [] 
app = None 

async def handle_video(client, message: Message):
    global video_queue
    msg = await message.reply("⏳ Видео в очереди! Открой страницу 'Добавить' на сайте.")
    
    fwd = await message.forward(CHANNEL_ID)
    stream_link = f"{BASE_URL}/stream/{fwd.id}"
    title = message.caption if message.caption else f"Видео {fwd.id}"

    # Добавляем в список для сайта
    video_queue.append({"title": title, "url": stream_link})

async def get_queue_handler(request):
    headers = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}
    if not video_queue: return web.json_response({"status": "empty"}, headers=headers)
    return web.json_response(video_queue.pop(0), headers=headers)

async def stream_handler(request):
    try:
        msg_id = int(request.match_info['msg_id'])
        msg = await app.get_messages(CHANNEL_ID, msg_id)
        media = msg.video or msg.document
        resp = web.StreamResponse(status=200, headers={"Content-Type": "video/mp4", "Accept-Ranges": "bytes"})
        await resp.prepare(request)
        async for chunk in app.stream_media(media): await resp.write(chunk)
        return resp
    except: return web.Response(status=404)

async def run_bot():
    global app
    app = Client("paritube_sync", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
    app.add_handler(hydrogram.handlers.MessageHandler(handle_video, filters.video | filters.document))
    import hydrogram.handlers
    await app.start()
    
    server = web.Application()
    server.add_routes([web.get('/stream/{msg_id}', stream_handler), web.get('/get_new_video', get_queue_handler)])
    runner = web.AppRunner(server)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8080).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(run_bot())
    
    print("🚀 Бот онлайн!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        pass
