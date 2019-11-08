import datetime
import logging

from sqlalchemy import TEXT
from sqlalchemy import Column
from sqlalchemy_utc import UtcDateTime

from pajbot.managers.db import Base

log = logging.getLogger("pajbot")


class LongTimeout(Base):
    __tablename__ = "long_timeout"

    username = Column(TEXT, primary_key=True, nullable=False, unique=True)
    timeout_start = Column(UtcDateTime(), nullable=False)
    timeout_recent_end = Column(UtcDateTime())
    timeout_end = Column(UtcDateTime(), nullable=False)
    timeout_author = Column(TEXT, nullable=False)

    def __init__(
        self,
        username,
        timeout_start,
        timeout_end,
        timeout_author,
        timeout_recent_end=(datetime.datetime.now() + datetime.timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S"),
    ):
        self.username = username
        self.timeout_start = timeout_start
        self.timeout_recent_end = timeout_recent_end
        self.timeout_end = timeout_end
        self.timeout_author = timeout_author
