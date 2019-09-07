import logging

import requests

from pajbot.managers.db import DBManager
from pajbot.models.command import Command
from pajbot.models.dotabet import DotaBetBet
from pajbot.models.duel import UserDuelStats
from pajbot.models.roulette import Roulette
from pajbot.models.user import User
from pajbot.modules import BaseModule

log = logging.getLogger(__name__)


class RenameModule(BaseModule):
    AUTHOR = "DatGuy1"
    ID = __name__.split(".")[-1]
    NAME = "Rename finder"
    DESCRIPTION = "Check if a user has renamed, and if so transfer their information"
    CATEGORY = "Feature"

    def load_commands(self, **options):
        self.commands["renamecheck"] = Command.raw_command(
            self.check_rename,
            delay_all=0,
            delay_user=60,
            description="Check if you're eligible for information transfer from one username to another",
        )

    def check_rename(self, **options):
        bot = options["bot"]
        source = options["source"]

        searchURL = "https://twitch-tools.rootonline.de/username_changelogs_search.php?q={}&format=json".format(
            source.username
        )

        r = requests.get(searchURL)
        if r.status_code != 200:
            log.warning("Error while connecting to twitch-tools.rootonline.de: " + r.status_code)
            return False

        parsedText = r.json()
        if not parsedText:
            bot.whisper(source.username, "No old usernames of yours have been found.")
            return False

        self.transfer_info(bot, source, parsedText[0]["username_old"])

    def transfer_info(self, bot, source, oldUsername):
        duelExists = True
        oldUserID = 0
        with bot.users.find_context(oldUsername) as oldUser:
            if not oldUser:
                bot.whisper(source.username, "Your old username is not in the database.")
                return False

            oldUserID = oldUser.id

            source.banned = oldUser.banned or source.banned
            source.ignored = oldUser.ignored or source.ignored
            source.level = oldUser.level if oldUser.level > source.level else source.level
            source.minutes_in_chat_offline = source.minutes_in_chat_offline + oldUser.minutes_in_chat_offline
            source.minutes_in_chat_online = source.minutes_in_chat_online + oldUser.minutes_in_chat_online
            # source.num_lines = source.num_lines + oldUsername.num_lines
            source.points = source.points + oldUser.points

        # Preferably this will all be incorporated into the above
        with DBManager.create_session_scope() as session:
            userModel = session.query(User).filter_by(username=oldUsername).one_or_none()

            oldDuelModel = session.query(UserDuelStats).filter_by(user_id=oldUserID).one_or_none()
            curDuelModel = session.query(UserDuelStats).filter_by(user_id=source.id).one_or_none()

            if not curDuelModel:
                duelExists = False
                curDuelModel = UserDuelStats(user_id=source.id)

            if oldDuelModel:
                curDuelModel.duels_won = curDuelModel.duels_won + oldDuelModel.duels_won
                curDuelModel.duels_total = curDuelModel.duels_total + oldDuelModel.duels_total
                curDuelModel.points_won = curDuelModel.points_won + oldDuelModel.points_won
                curDuelModel.points_lost = curDuelModel.points_lost + oldDuelModel.points_lost
                curDuelModel.longest_winstreak = (
                    oldDuelModel.longest_winstreak
                    if oldDuelModel.longest_winstreak > curDuelModel.longest_winstreak
                    else curDuelModel.longest_winstreak
                )
                curDuelModel.longest_losestreak = (
                    oldDuelModel.longest_losestreak
                    if oldDuelModel.longest_losestreak > curDuelModel.longest_losestreak
                    else curDuelModel.longest_losestreak
                )

            betModels = session.query(DotaBetBet).filter_by(user_id=oldUserID).all()
            rouletteModels = session.query(Roulette).filter_by(user_id=oldUserID).all()

            for betModel in betModels:
                betModel.user_id = source.id
            for rouletteModel in rouletteModels:
                rouletteModel.user_id = source.id

            session.delete(userModel)
            if oldDuelModel:
                session.delete(oldDuelModel)
            if not duelExists:
                session.add(curDuelModel)

        bot.whisper(source.username, "Everything has been successfully transferred")
