from . import handlers
import config


def setup_routes(app):
    app.router.add_get('/', handlers.index)
    app.router.add_post('/session', handlers.login)
    app.router.add_delete('/session', handlers.logout)

    app.router.add_static('/public/',
                          path=config.http_root.joinpath('public'),
                          name='public')