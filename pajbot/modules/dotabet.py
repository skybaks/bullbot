import logging

import requests

from pajbot import utils
from pajbot.actions import ActionQueue
from pajbot.exc import InvalidPointAmount
from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.dotabet import DotaBetBet
from pajbot.models.dotabet import DotaBetGame
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class ExitLoop(Exception):
    pass


class DotaBetModule(BaseModule):
    AUTHOR = "DatGuy1"
    ID = __name__.split(".")[-1]
    NAME = "DotA Betting"
    DESCRIPTION = "Enables betting on DotA 2 games with !dotabet"
    CATEGORY = "Game"

    SETTINGS = [
        ModuleSetting(  # Not required
            key="max_return", label="Maximum return odds", type="number", placeholder="", default="20"
        ),
        ModuleSetting(  # Not required
            key="min_return", label="Minimum return odds", type="text", placeholder="", default="1.10"
        ),
        ModuleSetting(
            key="steam3_id",
            label="Steam 3 ID of streamer (number only)",
            type="number",
            required=True,
            placeholder="",
            default="",
        ),
        ModuleSetting(key="api_key", label="Steam API Key", type="text", required=True, placeholder="", default=""),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.action_queue = ActionQueue()
        self.action_queue.start()
        self.bets = {}
        self.betting_open = False
        self.message_closed = True
        self.isRadiant = False
        self.matchID = 0
        self.oldID = 0
        self.winPoints = 0
        self.lossPoints = 0
        self.winBetters = 0
        self.lossBetters = 0
        self.gettingTeam = False
        self.secondAttempt = False
        self.calibrating = True
        self.calibratingSecond = True
        self.jobPaused = False
        self.spectating = False

        self.job = ScheduleManager.execute_every(25, self.poll_webapi)
        self.job.pause()

        self.reminder_job = ScheduleManager.execute_every(200, self.reminder_bet)
        self.reminder_job.pause()

        # self.finish_job = ScheduleManager.execute_every(60, self.get_game)
        # self.finish_job.pause()

        # self.close_job = ScheduleManager.execute_every(1200, self.bot.websocket_manager.emit, ("dotabet_close_game", ))
        # self.close_job.pause()

    def reminder_bet(self):
        if self.betting_open:
            self.bot.me("monkaS 👉 🕒 place your bets people")
            self.bot.websocket_manager.emit("notification", {"message": "monkaS 👉 🕒 place your bets people"})
        else:
            if not self.message_closed:
                winRatio, lossRatio = self.get_odds_ratio(self.winPoints, self.lossPoints)
                self.bot.me(
                    "The betting for the current game has been closed! Winners can expect a {:0.2f} (win betters) or {:0.2f} (loss betters) return "
                    "ratio".format(winRatio, lossRatio)
                )
                self.bot.websocket_manager.emit(
                    "notification", {"message": "The betting for the current game has been closed!"}
                )
                if not self.spectating:
                    self.bot.execute_delayed(15, self.bot.websocket_manager.emit, ("dotabet_close_game",))
                self.message_closed = True

    def reinit_params(self):
        self.winBetters = 0
        self.winPoints = 0
        self.lossBetters = 0
        self.lossPoints = 0
        self.bets = {}

    def get_odds_ratio(self, winPoints, lossPoints):
        solveFormula = lambda x, y: 1.0 + (float(x) / (float(y)))
        winRatio = solveFormula(lossPoints, winPoints)
        lossRatio = solveFormula(winPoints, lossPoints)

        ratioList = [winRatio, lossRatio]

        for c, curRatio in enumerate(ratioList):
            if self.maxReturn and curRatio > self.maxReturn:
                ratioList[c] = self.maxReturn
            if self.minReturn and curRatio < self.minReturn:
                ratioList[c] = self.minReturn

        return tuple(ratioList)

    def spread_points(self, gameResult):
        winners = 0
        losers = 0
        total_winnings = 0
        total_losings = 0

        if gameResult == "win":
            solveFormula = self.get_odds_ratio(self.winPoints, self.lossPoints)[0]
        else:
            solveFormula = self.get_odds_ratio(self.winPoints, self.lossPoints)[1]

        with DBManager.create_session_scope() as db_session:
            db_bets = {}
            for username in self.bets:
                bet_for_win, betPoints = self.bets[username]
                points = int(betPoints * solveFormula) + 1

                user = self.bot.users.find(username, db_session=db_session)
                if user is None:
                    continue

                correct_bet = (gameResult == "win" and bet_for_win is True) or (
                    gameResult == "loss" and bet_for_win is False
                )

                db_bets[username] = DotaBetBet(user.id, "win" if bet_for_win else "loss", betPoints, 0)

                if correct_bet:
                    winners += 1
                    total_winnings += points - betPoints
                    db_bets[username].profit = points
                    user.points += points
                    self.bot.whisper(
                        user.username,
                        "You bet {} points on the correct outcome and gained an extra {} points, "
                        "you now have {} points PogChamp".format(betPoints, points - betPoints, user.points),
                    )
                else:
                    losers += 1
                    total_losings += betPoints
                    db_bets[username].profit = -betPoints
                    self.bot.whisper(
                        user.username,
                        "You bet {} points on the wrong outcome, so you lost it all :( . You now have {} points admiralCute".format(
                            betPoints, user.points
                        ),
                    )

        startString = (
            "The game ended as a {}. {} users won an extra {} points, while {}"
            " lost {} points. Winners can expect a {:0.2f} return ratio.".format(
                gameResult, winners, total_winnings, losers, total_losings, solveFormula
            )
        )

        if self.spectating:
            resultString = startString[:20] + "radiant " + startString[20:]
        else:
            resultString = startString

        # for username in db_bets:
        #     bet = db_bets[username]
        #     db_session.add(bet)
        #     db_session.commit()

        self.betting_open = False
        self.message_closed = True
        self.reinit_params()

        bet_game = DotaBetGame(gameResult, total_winnings - total_losings, winners, losers)

        db_session.add(bet_game)

        self.bot.websocket_manager.emit("notification", {"message": resultString, "length": 8})
        self.bot.me(resultString)

    def get_game(self):
        gameResult = "loss"
        # log.debug(self.isRadiant)

        odURL = "https://api.opendota.com/api/players/{}/recentMatches".format(self.settings["steam3_id"])
        gameHistory = requests.get(odURL).json()[0]

        if gameHistory["match_id"] != self.matchID:
            self.matchID = gameHistory["match_id"]

            if self.calibrating:
                self.calibrating = False
                return

            if self.isRadiant and gameHistory["radiant_win"]:
                gameResult = "win"
            else:
                if not self.isRadiant and not gameHistory["radiant_win"]:
                    gameResult = "win"
                else:
                    gameResult = "loss"
            # log.error(gameResult)
            self.spread_points(gameResult)

    def poll_webapi(self):
        serverID = ""

        with open("/srv/admiralbullbot/configs/currentID.txt", "r") as f:
            serverID = f.read()

        try:
            serverID = int(serverID)
        except ValueError:
            return False

        if self.calibratingSecond and serverID != 0:
            self.calibratingSecond = False
            return False

        if serverID == 0:
            self.bot.execute_delayed(100, self.close_shit)
            return False

        if self.oldID == serverID:
            return False

        self.oldID = serverID

        self.bot.execute_delayed(12, self.get_team, (serverID,))

    def startGame(self):
        if not self.betting_open:
            self.betting_open = True
            self.message_closed = False
            self.reinit_params()
            self.bot.websocket_manager.emit("dotabet_new_game")

        bulldogTeam = "radiant" if self.isRadiant else "dire"
        openString = "A new game has begun! Bulldog is on {}. Vote with !dotabet win/lose POINTS".format(bulldogTeam)

        self.bot.websocket_manager.emit("notification", {"message": openString})
        # self.bot.websocket_manager.emit("dotabet_new_game")

        self.bot.me(openString)

    def get_team(self, serverID):
        attempts = 0
        if not serverID:
            return

        webURL = (
            "https://api.steampowered.com/IDOTA2MatchStats_570/GetRealtimeStats/v1?"
            "server_steam_id={}&key={}".format(serverID, self.settings["api_key"])
        )
        jsonText = requests.get(webURL).json()

        try:
            while not jsonText:  # Could bug and not return anything
                if attempts > 60:
                    if not self.secondAttempt:
                        self.bot.execute_delayed(20, self.get_team, (serverID,))
                        self.secondAttempt = True
                    else:
                        self.bot.say(
                            'Couldn"t find which team Bulldog is on for this game. Mods - handle this round manually :)'
                        )
                        self.job.pause()
                        self.jobPaused = True
                        self.secondAttempt = False

                    attempts = 0
                    return

                attempts += 1
                jsonText = requests.get(webURL).json()
                log.debug(jsonText)

                try:
                    self.gettingTeam = True
                    for i in range(2):
                        for player in jsonText["teams"][i]["players"]:
                            log.debug(player["name"])
                            if player["accountid"] == self.settings["steam3_id"]:
                                if i == 0:
                                    self.isRadiant = True
                                else:
                                    self.isRadiant = False
                                self.bot.me(
                                    'Is bulldog on radiant? {}. If he isn"t then tag a mod with BabyRage fix '
                                    "bet".format(self.isRadiant)
                                )
                                raise ExitLoop
                except KeyError:
                    jsonText = ""

        except ExitLoop:
            pass

        self.gettingTeam = False
        self.betting_open = True
        self.secondAttempt = False
        self.startGame()

    def command_open(self, **options):
        openString = "Betting has been opened"
        bot = options["bot"]
        message = options["message"]
        self.calibrating = True

        if message:
            if "dire" in message:
                self.isRadiant = False
            elif "radi" in message:
                self.isRadiant = True
            elif "spectat" in message:
                self.isRadiant = True
                self.spectating = True
                openString += ". Reminder to bet with radiant/dire instead of win/loss"
                self.calibrating = False

        if not self.betting_open:
            bot.websocket_manager.emit("notification", {"message": openString})
            if not self.spectating:
                bot.websocket_manager.emit("dotabet_new_game")
            bot.me(openString)

        self.betting_open = True
        self.message_closed = False
        self.job.pause()
        self.jobPaused = True

    def command_stats(self, **options):
        bot = options["bot"]
        source = options["source"]

        bot.say(
            "{}/{} betters on {}/{} points".format(self.winBetters, self.lossBetters, self.winPoints, self.lossPoints)
        )

    def close_shit(self):
        if self.jobPaused:
            return False

        self.betting_open = False
        self.reminder_bet()

    def command_close(self, **options):
        bot = options["bot"]
        source = options["source"]
        message = options["message"]

        if self.betting_open:
            count_down = 15
            if message and message.isdigit():
                count_down = int(message)
            if count_down > 0:
                bot.me("Betting will be locked in {} seconds! Place your bets people monkaS".format(count_down))
            bot.execute_delayed(count_down, self.lock_bets, (bot,))
        elif message:
            if "l" in message.lower() or "dire" in message.lower():
                self.spread_points("loss")
            elif "w" in message.lower() or "radi" in message.lower():
                self.spread_points("win")
            else:
                bot.whisper(source.username, "Are you pretending?")
                return False

            self.calibrating = True
            self.spectating = False

    def lock_bets(self, bot):
        self.betting_open = False
        self.reminder_bet()
        self.job.resume()
        self.jobPaused = False

    def command_restart(self, **options):
        bot = options["bot"]
        message = options["message"]
        source = options["source"]
        reason = ""

        if not message:
            reason = "No reason given EleGiggle"
        else:
            reason = message

        with DBManager.create_session_scope() as db_session:
            for username in self.bets:
                bet_for_win, betPoints = self.bets[username]
                user = self.bot.users.find(username, db_session=db_session)
                if not user:
                    continue

                user.points += betPoints
                bot.whisper(
                    user.username,
                    "Your {} points bet has been refunded. The reason given is: " "{}".format(betPoints, reason),
                )

        self.betting_open = False
        self.message_closed = True

        self.reinit_params()

        bot.me("All your bets have been refunded and betting has been restarted.")

    def command_resetbet(self, **options):
        options["bot"].me("The bets have been reset :)")
        self.reinit_params()

    def command_betstatus(self, **options):
        bot = options["bot"]
        if self.betting_open:
            bot.say("Betting is open")
        elif self.winBetters > 0 or self.lossBetters > 0:
            bot.say("There is currently a bet with points not given yet")
        else:
            bot.say("There is no bet running")

    def command_bet(self, **options):
        bot = options["bot"]
        source = options["source"]
        message = options["message"]

        if message is None:
            return False

        if not self.betting_open:
            bot.whisper(source.username, "Betting is not currently open. Wait until the next game :\\")
            return False

        msg_parts = message.split(" ")
        if len(msg_parts) < 2:
            bot.whisper(
                source.username,
                "Invalid bet. You must do !dotabet radiant/dire POINTS (if spectating a game) "
                "or !dotabet win/loss POINTS (if playing)",
            )
            return False

        if source.username in self.bets:
            bot.whisper(source.username, "You have already bet on this game. Wait until the next game starts!")
            return False

        points = 0
        try:
            points = utils.parse_points_amount(source, msg_parts[1])
            if points > 2000:
                points = 2000
        except InvalidPointAmount as e:
            bot.whisper(
                source.username,
                "Invalid bet. You must do !dotabet radiant/dire POINTS (if spectating a game) "
                "or !dotabet win/loss POINTS (if playing) {}".format(e),
            )
            return False

        if points < 1:
            bot.whisper(source.username, "You can't bet less than 1 point you goddamn pleb Bruh")
            return False

        if not source.can_afford(points):
            bot.whisper(source.username, "You don't have {} points to bet".format(points))
            return False

        outcome = msg_parts[0].lower()
        bet_for_win = False

        if "w" in outcome or "radi" in outcome:
            bet_for_win = True

        elif "l" in outcome or "dire" in outcome:
            bet_for_win = False
        else:
            bot.whisper(
                source.username,
                "Invalid bet. You must do !dotabet radiant/dire POINTS (if spectating a game) "
                "or !dotabet win/loss POINTS (if playing)",
            )
            return False

        if bet_for_win:
            self.winBetters += 1
            self.winPoints += points
        else:
            self.lossBetters += 1
            self.lossPoints += points

        source.points -= points
        self.bets[source.username] = (bet_for_win, points)

        payload = {
            "win_betters": self.winBetters,
            "loss_betters": self.lossBetters,
            "win_points": self.winPoints,
            "loss_points": self.lossPoints,
        }

        if not self.spectating:
            bot.websocket_manager.emit("dotabet_update_data", data=payload)

        finishString = "You have bet {} points on this game resulting in a ".format(points)
        if self.spectating:
            finishString = finishString + "radiant "

        bot.whisper(source.username, "{}{}".format(finishString, "win" if bet_for_win else "loss"))

    def load_commands(self, **options):
        self.commands["dotabet"] = Command.raw_command(
            self.command_bet,
            delay_all=0,
            delay_user=0,
            can_execute_with_whisper=True,
            description="Bet points",
            examples=[
                CommandExample(
                    None,
                    "Bet 69 points on a win",
                    chat="user:!dotabet win 69\n" "bot>user: You have bet 69 points on this game resulting in a win.",
                    description="Bet that the streamer will win for 69 points",
                ).parse()
            ],
        )
        self.commands["bet"] = self.commands["dotabet"]

        self.commands["openbet"] = Command.raw_command(
            self.command_open, level=420, delay_all=0, delay_user=0, description="Open bets"
        )
        self.commands["restartbet"] = Command.raw_command(
            self.command_restart, level=420, delay_all=0, delay_user=0, description="Restart bets"
        )
        self.commands["closebet"] = Command.raw_command(
            self.command_close, level=420, delay_all=0, delay_user=0, description="Close bets"
        )
        self.commands["resetbet"] = Command.raw_command(self.command_resetbet, level=500, description="Reset bets")
        self.commands["betstatus"] = Command.raw_command(
            self.command_betstatus, level=420, description="Status of bets"
        )
        self.commands["currentbets"] = Command.raw_command(self.command_stats, level=100, delay_all=0, delay_user=10)
        # self.commands["betstats"]

    def enable(self, bot):
        if bot:
            self.job.resume()
            self.reminder_job.resume()
            # self.finish_job.resume()
            # self.close_job.resume()
        self.bot = bot

        # Move this to somewhere better
        self.maxReturn = self.settings["max_return"] if "max_return" in self.settings else None
        self.minReturn = float(self.settings["min_return"]) if "min_return" in self.settings else None

    def disable(self, bot):
        if bot:
            self.job.pause()
            self.reminder_job.pause()
            # self.finish_job.pause()
            # self.close_job.pause()
