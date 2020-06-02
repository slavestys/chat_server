from tortoise import Tortoise
from alembic.config import Config


__alembic_cfg = Config("alembic.ini")
__db_dns = __alembic_cfg.get_section_option('alembic', 'sqlalchemy.url')


async def init():
    # Here we create a SQLite DB using file "db.sqlite3"
    #  also specify the app name of "models"
    #  which contain models from "app.models"
    await Tortoise.init(
        db_url=__db_dns,
        modules={'models': ['models']}
    )
    # Generate the schema
    #await Tortoise.generate_schemas()