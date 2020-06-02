from aiohttp import web

from http_server.templates_setup import jinja_env


async def index(request):
    template = jinja_env.get_template('index.html')
    return web.Response(body=template.render({'current_user': request.current_user}), content_type='text/html')