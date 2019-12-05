import datetime
import logging

from sqlalchemy import Column, INT, TEXT
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy_utc import UtcDateTime

from pajbot import utils
from pajbot.managers.db import Base

log = logging.getLogger("pajbot")


class LongTimeout(Base):
    __tablename__ = "long_timeout"

    id = Column(INT, primary_key=True)
    user_id = Column(INT, ForeignKey("user.id", ondelete="CASCADE"), index=True, nullable=False)
    timeout_start = Column(UtcDateTime(), nullable=False)
    timeout_recent_end = Column(UtcDateTime())
    timeout_end = Column(UtcDateTime(), nullable=False)
    timeout_author = Column(TEXT, nullable=False)

    user = relationship("User")

    def __init__(
        self,
        user_id,
        timeout_start,
        timeout_end,
        timeout_author,
        timeout_recent_end=(utils.now() + datetime.timedelta(days=14)),
    ):
        self.user_id = user_id
        self.timeout_start = timeout_start
        self.timeout_recent_end = timeout_recent_end
        self.timeout_end = timeout_end
        self.timeout_author = timeout_author

    user = relationship("User")
