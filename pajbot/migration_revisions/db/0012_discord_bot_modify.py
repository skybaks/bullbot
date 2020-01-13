import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    # new: tier record
    cursor.execute('ALTER TABLE "user" ADD COLUMN tier INTEGER DEFAULT NULL')

    # new: last_pair record
    cursor.execute('ALTER TABLE "user" ADD COLUMN last_pair TIMESTAMPTZ DEFAULT NULL')

    cursor.execute(
    """
    CREATE TABLE user_connections (
        twitch_id TEXT PRIMARY KEY NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        twitch_login TEXT DEFAULT NULL,
        discord_user_id TEXT UNIQUE,
        steam_id TEXT UNIQUE,
        discord_username TEXT
    )
    """
    )
