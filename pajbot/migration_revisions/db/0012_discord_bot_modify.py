import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    # new: tier record
    cursor.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS tier INTEGER DEFAULT NULL')

    # new: last_pair record
    cursor.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS last_pair TIMESTAMPTZ DEFAULT NULL')

    cursor.execute(
        """
    CREATE TABLE user_connections (
        twitch_id TEXT PRIMARY KEY NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        twitch_login TEXT DEFAULT NULL,
        discord_user_id TEXT UNIQUE,
        discord_username TEXT,
        discord_tier INTEGER DEFAULT NULL,
        steam_id TEXT UNIQUE
    )
    """
    )
