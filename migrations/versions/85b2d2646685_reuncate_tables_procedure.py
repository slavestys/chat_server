"""reuncate tables procedure

Revision ID: 85b2d2646685
Revises: d8b0c689d31c
Create Date: 2020-06-25 12:57:46.924010

"""
from alembic import op
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision = '85b2d2646685'
down_revision = 'd8b0c689d31c'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_development():
    pass


def downgrade_development():
    pass


def upgrade_test():
    conn = op.get_bind()
    conn.execute(
        text(
            """
                CREATE OR REPLACE FUNCTION truncate_tables() RETURNS void AS $$
                DECLARE
                    statements CURSOR FOR
                        SELECT tablename FROM pg_tables
                        WHERE schemaname = 'public' AND tablename <> 'alembic_version';
                BEGIN
                    FOR stmt IN statements LOOP
                        EXECUTE 'TRUNCATE TABLE ' || quote_ident(stmt.tablename) || ' CASCADE;';
                    END LOOP;
                END;
                $$ LANGUAGE plpgsql;
            """
        )
    )


def downgrade_test():
    conn = op.get_bind()
    conn.execute(text('DROP FUNCTION IF EXISTS truncate_tables()'))

