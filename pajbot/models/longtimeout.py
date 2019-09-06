import datetime
import logging

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import String

from pajbot.managers.db import Base

log = logging.getLogger("pajbot")


class LongTimeout(Base):
    __tablename__ = "tb_longtimeout"

    username = Column(String(32), primary_key=True, nullable=False, unique=True)
    timeout_start = Column(DateTime, nullable=False)
    timeout_recent_end = Column(DateTime)
    timeout_end = Column(DateTime, nullable=False)
    timeout_author = Column(String(32), nullable=False)

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
