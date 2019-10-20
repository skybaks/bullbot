import logging

from sqlalchemy import INT
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy_utc import UtcDateTime

from pajbot import utils
from pajbot.managers.db import Base

log = logging.getLogger("pajbot")


class BetGame(Base):
    __tablename__ = "bet_game"

    id = Column(INT, primary_key=True)
    internal_id = Column(UtcDateTime(), default=utils.now())
    outcome = Column(Enum("win", "loss", name="bet_outcome"), nullable=False)
    points_change = Column(INT, nullable=False)
    win_bettors = Column(INT, nullable=False)
    loss_bettors = Column(INT, nullable=False)

    def __init__(self, outcome, points_change, win_bettors, loss_bettors):
        self.outcome = outcome
        self.points_change = points_change
        self.win_bettors = win_bettors
        self.loss_bettors = loss_bettors
