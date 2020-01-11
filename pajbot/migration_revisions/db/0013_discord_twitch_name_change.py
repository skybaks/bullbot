import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    # new: tier record
    cursor.execute('ALTER TABLE "user_connections" ADD COLUMN twitch_login text DEFAULT NULL')
