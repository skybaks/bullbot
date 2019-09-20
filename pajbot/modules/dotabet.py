import logging

from pajbot import utils
from pajbot.exc import InvalidPointAmount
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.dotabet import DotaBetBet
from pajbot.models.dotabet import DotaBetGame
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


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
        ModuleSetting(key="max_bet", label="Maximum bet", type="number", placeholder="", default="2000"),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

        self.reinit_params()
        self.betting_open = False
        self.message_closed = True
        self.spectating = False

        self.reminder_job = ScheduleManager.execute_every(200, self.reminder_bet)
        self.reminder_job.pause()

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

    def create_solve_formula(self, x, y):
        return 1.0 + (float(x) / (float(y)))

    def get_odds_ratio(self, winPoints, lossPoints):
        if lossPoints == 0:
            lossPoints = 1
        if winPoints == 0:
            winPoints = 1

        winRatio = self.create_solve_formula(lossPoints, winPoints)
        lossRatio = self.create_solve_formula(winPoints, lossPoints)

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
                    userObject = db_session.query(User).with_for_update().filter_by(username=username).first()
                    userObject.points = userObject.points + points
                    self.bot.whisper(
                        user.username,
                        "You bet {} points on the correct outcome and gained an extra {} points, "
                        "you now have {} points PogChamp".format(betPoints, points - betPoints, userObject.points),
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

    def automated_end(self, winning_team, player_team):
        self.bot.say("Closing bet automatically...")
        if winning_team == player_team:
            self.bot.execute_delayed(0.2, self.spread_points, ("win",))
        else:
            self.bot.execute_delayed(0.2, self.spread_points, ("loss",))

    def automated_lock(self):
        self.bot.execute_delayed(15, self.lock_bets)
        self.bot.me("Betting will be locked in 15 seconds! Place your bets people monkaS")

    def lock_bets(self):
        self.betting_open = False
        self.reminder_bet()

    def start_game(self, openString=None):
        if not openString:
            openString = "A new game has begun! Vote with !bet win/lose POINTS"

        if not self.betting_open:
            self.bot.websocket_manager.emit("notification", {"message": openString})
            if not self.spectating:
                self.bot.websocket_manager.emit("dotabet_new_game")
            self.bot.me(openString)

        self.betting_open = True
        self.message_closed = False

    def command_open(self, **options):
        openString = "Betting has been opened"
        message = options["message"]

        if message and ["dire", "radi", "spectat"] in message:
            self.spectating = True
            openString += ". Reminder to bet with radiant/dire instead of win/loss"

        self.start_game()

    def command_stats(self, **options):
        bot = options["bot"]

        bot.say(
            "{}/{} betters on {}/{} points".format(self.winBetters, self.lossBetters, self.winPoints, self.lossPoints)
        )

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
            bot.execute_delayed(count_down, self.lock_bets)
        elif message:
            if "l" in message.lower() or "dire" in message.lower():
                bot.execute_delayed(0.2, self.spread_points, ("loss",))
            elif "w" in message.lower() or "radi" in message.lower():
                bot.execute_delayed(0.2, self.spread_points, ("win",))
            else:
                bot.say("Are you pretending {}?".format(source.username_raw))
                return False

            self.calibrating = True
            self.spectating = False

    def command_restart(self, **options):
        bot = options["bot"]
        message = options["message"]
        reason = ""

        if message:
            reason = message
        else:
            reason = "No reason given EleGiggle"

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
                "Invalid bet. You must do !bet radiant/dire POINTS (if spectating a game) "
                "or !bet win/loss POINTS (if playing)",
            )
            return False

        if source.username in self.bets:
            bot.whisper(source.username, "You have already bet on this game. Wait until the next game starts!")
            return False

        points = 0
        try:
            points = utils.parse_points_amount(source, msg_parts[1])
            if points > self.settings["max_bet"]:
                points = self.settings["max_bet"]
        except InvalidPointAmount as e:
            bot.whisper(
                source.username,
                "Invalid bet. You must do !bet radiant/dire POINTS (if spectating a game) "
                "or !bet win/loss POINTS (if playing) {}".format(e),
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
                "Invalid bet. You must do !bet radiant/dire POINTS (if spectating a game) "
                "or !bet win/loss POINTS (if playing)",
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
        self.commands["bet"] = Command.raw_command(
            self.command_bet,
            delay_all=0,
            delay_user=0,
            can_execute_with_whisper=True,
            description="Bet points",
            examples=[
                CommandExample(
                    None,
                    "Bet 69 points on a win",
                    chat="user:!bet win 69\n" "bot>user: You have bet 69 points on this game resulting in a win.",
                    description="Bet 69 points that the streamer will win",
                ).parse()
            ],
        )
        self.commands["dotabet"] = self.commands["bet"]

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

    def enable(self, bot):
        HandlerManager.add_handler("on_open_bets", self.start_game)
        HandlerManager.add_handler("on_lock_bets", self.automated_lock)
        HandlerManager.add_handler("on_end_bets", self.automated_end)

        self.reminder_job.resume()

        # Move this somewhere better hopefully
        self.maxReturn = self.settings["max_return"] if "max_return" in self.settings else None
        self.minReturn = float(self.settings["min_return"]) if "min_return" in self.settings else None

    def disable(self, bot):
        HandlerManager.remove_handler("on_open_bets", self.start_game)
        HandlerManager.remove_handler("on_lock_bets", self.automated_lock)
        HandlerManager.remove_handler("on_end_bets", self.automated_end)

        self.reminder_job.pause()
