import logging

from sqlalchemy import TEXT, INT
from sqlalchemy import Column
from sqlalchemy import ForeignKey

from pajbot.managers.db import Base

log = logging.getLogger(__name__)


class UserConnections(Base):
    __tablename__ = "user_connections"

    # Twitch user ID
    twitch_id = Column(INT, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, autoincrement=False)
    twitch_login = Column(TEXT, nullable=False)

    # Discord user id
    discord_user_id = Column(TEXT, nullable=False)
    discord_username = Column(TEXT, nullable=False)

    # steamID64
    steam_id = Column(TEXT, nullable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def jsonify(self):
        return {
            "twitch_id": self.twitch_id,
            "twitch_login": self.twitch_login,
            "discord_user_id": self.discord_user_id,
            "discord_username": self.discord_username,
            "steam_id": self.steam_id,
        }

    def __eq__(self, other):
        if not isinstance(other, UserConnections):
            return False
        return self.twitch_id == other.twitch_id

    def _remove(self, db_session):
        db_session.delete(self)

    def _update_discord_username(self, db_session, discord_username):
        self.discord_username = discord_username
        db_session.merge(self)
        return self

    def _update_twitch_login(self, db_session, twitch_login):
        self.twitch_login = twitch_login
        db_session.merge(self)
        return self

    @staticmethod
    def _create(db_session, twitch_id, discord_user_id, disord_username, steam_id):
        user_con = UserConnections(
            twitch_id=twitch_id, discord_user_id=discord_user_id, disord_username=disord_username, steam_id=steam_id
        )
        db_session.add(user_con)
        return user_con
