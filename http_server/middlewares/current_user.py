from aiohttp import web
import json

from models import User, FakeUser


async def __set_current_user(request: web.Request):
    if request.path.startswith('/public'):
        return
    try:
        print(f'Set current user: {request.url}')
        user_json = request.cookies.get('user')
        if user_json:
            user_data = json.loads(user_json)
            user = await User.filter(id=int(user_data['id'])).first()
            if user and user.key() == user_data['key']:
                request.current_user = user
            else:
                request.current_user = FakeUser()
        else:
            request.current_user = FakeUser()
    except Exception:
        request.current_user = FakeUser()

@web.middleware
async def current_user(request: web.Request, handler):
    await __set_current_user(request)
    resp = await handler(request)
    return resp