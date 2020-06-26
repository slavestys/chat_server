import db
from aiohttp import web

from chat_server import Chat, ChatState

class ChatServer:
    _chat: Chat = None
    _app: web.Application = None

    @property
    def chat(self) -> Chat:
        return self._chat

    @property
    def state(self) -> ChatState:
        return self._chat.state

    @property
    def app(self) -> web.Application:
        return self._app

    async def setup_app(self):
        await db.init()
        self._app = web.Application()

        self._chat = Chat()
        self._app.router.add_get('/', self._chat.accept)
        self._app.on_cleanup.append(self._chat.shutdown)
        return self._app


if __name__ == '__main__':
    server = ChatServer()
    web.run_app(server.setup_app(), port=8765)




