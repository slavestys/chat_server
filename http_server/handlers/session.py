from aiohttp import web

from models import User


async def login(request: web.BaseRequest):
    parameters = await request.json()
    user = await User.get_or_none(name=parameters.get('login'), passwd=parameters.get('password'))
    if user:
        response = web.json_response({'status': 'ok', 'user': user.client_data()})
        response.cookies['user'] = user.json_data()
        return response
    else:
        return web.json_response({'status': 'error'})


async def logout(request: web.BaseRequest):
    response = web.json_response({'status': 'ok'})
    response.cookies['user'] = None
    return response
