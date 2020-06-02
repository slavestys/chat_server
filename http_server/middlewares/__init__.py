from .current_user import current_user as __current_user


def setup(app):
    app.middlewares.append(__current_user)
