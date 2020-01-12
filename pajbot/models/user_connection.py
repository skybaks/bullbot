import logging

from sqlalchemy import TEXT
from sqlalchemy import Column
from sqlalchemy import ForeignKey

from pajbot.managers.db import Base

log = logging.getLogger(__name__)


class UserConnections(Base):
    __tablename__ = "user_connections"

    # Twitch user ID
    twitch_id = Column(TEXT, ForeignKey("user.id", ondelete=""), primary_key=True, nullable=False)
    twitch_login = Column(TEXT, nullable=False)

    # Discord user id
    discord_user_id = Column(TEXT, nullable=False)
    disord_username = Column(TEXT, nullable=False)

    # steamID64
    steam_id = Column(TEXT, nullable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def jsonify(self):
        return {
            "twitch_id": self.twitch_id,
            "twitch_login": self.twitch_login,
            "discord_user_id": self.discord_user_id,
            "disord_username": self.disord_username,
            "steam_id": self.steam_id,
        }

    def __eq__(self, other):
        if not isinstance(other, UserConnections):
            return False
        return self.twitch_id == other.twitch_id

    def _remove(self, db_session):
        db_session.delete(self)

    def _update_disord_username(self, db_session, disord_username):
        self.disord_username = disord_username
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
