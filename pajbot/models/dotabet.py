import datetime
import logging

from sqlalchemy import INT
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy_utc import UtcDateTime

from pajbot.managers.db import Base

log = logging.getLogger("pajbot")


class DotaBetGame(Base):
    __tablename__ = "dotabet_game"

    id = Column(INT, primary_key=True)
    internal_id = Column(UtcDateTime(), default=datetime.datetime.now())
    outcome = Column(Enum("win", "loss", name="dotabet_outcome"), nullable=False)
    points_change = Column(INT, nullable=False)
    win_bettors = Column(INT, nullable=False)
    loss_bettors = Column(INT, nullable=False)

    def __init__(self, outcome, points_change, win_bettors, loss_bettors):
        self.outcome = outcome
        self.points_change = points_change
        self.win_bettors = win_bettors
        self.loss_bettors = loss_bettors


class DotaBetBet(Base):
    __tablename__ = "dotabet_bet"

    id = Column(INT, primary_key=True)
    game_time = Column(UtcDateTime(), default=datetime.datetime.now())
    user_id = Column(INT, nullable=False, index=True)  # TODO: Change this to foreign key, same as duel_stats
    outcome = Column(Enum("win", "loss", name="dotabet_outcome"), nullable=False)
    points = Column(INT, nullable=False)
    profit = Column(INT, nullable=False)

    def __init__(self, user_id, outcome, points, profit):
        self.user_id = user_id
        self.outcome = outcome
        self.points = points
        self.profit = profit
