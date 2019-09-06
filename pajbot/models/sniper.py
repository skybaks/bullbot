import time

from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import Column

from pajbot.managers.db import Base


class SniperLeaderboards(Base):
    __tablename__ = "tb_sniperboards"

    username = Column(String(32), primary_key=True, nullable=False)
    kills = Column(TINYINT(1), nullable=False)
    recent_kill = Column(DATETIME, nullable=False)

    def __init__(self, username, recent_kill = None, kills = 0):
        self.username = username
        self.recent_kill = recent_kill
        self.kills = kills

class SniperSubmissions(Base):
    __tablename__ = "tb_snipersubmissions"

    id = Column(Integer, primary_key=True)
    username = Column(String(32), nullable=False)
    link = Column(String(128), unique=True, nullable=False)
    submission_time = Column(DATETIME, nullable=False, default=time.strftime("%Y-%m-%d %H:%M:%S"))

    def __init__(self, username, link, submission_time = time.strftime("%Y-%m-%d %H:%M:%S")):
        self.id = 0
        self.username = username
        self.link = link
        self.submission_time = submission_time
