from aiohttp import web

import db
from http_server import setup_routes
from http_server import setup_middlewares


async def main():
    await db.init()
    app = web.Application()
    setup_routes(app)
    setup_middlewares(app)
    return app

web.run_app(main(), port=3000)