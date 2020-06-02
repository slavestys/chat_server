import db
from aiohttp import web

from chat_server import Chat


async def main():
    await db.init()
    app = web.Application()

    chat = Chat()
    app.router.add_get('/', chat.accept)
    app.on_cleanup.append(chat.shutdown)
    return app

web.run_app(main(), port=8765)




