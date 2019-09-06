import logging
from unidecode import unidecode

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class EmoteCounterModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Emote Counter"
    DESCRIPTION = "Display a counter with two different emotes on screen"
    CATEGORY = "Feature"

    def __init__(self, bot):
        super().__init__(bot)
        self.bot = None
        self.votingOpen = False
        self.usageResponse = "Invalid usage. !emotecounter emote1 emote2 duration"
        self.votedUsers = []
        self.emoteNames = []
        self.emoteValues = [0, 0]

    def emote_counter(self, **options):
        bot = options["bot"]
        source = options["source"]
        message = options["message"]
        args = options["args"]

        msg_parts = message.split(" ")

        if self.votingOpen:
            bot.whisper(source.username, "Voting is already open.")
            return False

        if len(msg_parts) < 3 or len(args["emote_instances"]) < 2:
            bot.whisper(source.username, self.usageResponse)
            return False

        first_emote = args["emote_instances"][0].emote
        second_emote = args["emote_instances"][1].emote

        self.emoteNames.extend([first_emote.code, second_emote.code])
        payload = {"emote1": first_emote.jsonify(), "emote2": second_emote.jsonify()}
        try:
            duration = int(msg_parts[2])
        except ValueError:
            bot.whisper(source.username, self.usageResponse)
            return False

        self.votingOpen = True
        bot.websocket_manager.emit("emotecounter_start", payload)
        bot.say(
            "It's time to start voting for {} or {} ! You only get one vote.".format(
                first_emote.code, second_emote.code
            )
        )
        HandlerManager.add_handler("on_message", self.on_message)
        bot.execute_delayed(duration, self.cleanup_counter, ({}))

    def cleanup_counter(self, **options):
        winnerText = ""
        if self.emoteValues[0] > self.emoteValues[1]:
            winnerText = "{} won with {} votes while {} had {} votes".format(
                self.emoteNames[0], self.emoteValues[0], self.emoteNames[1], self.emoteValues[1]
            )
        elif self.emoteValues[1] > self.emoteValues[0]:
            winnerText = "{} won with {} votes while {} had {} votes".format(
                self.emoteNames[1], self.emoteValues[1], self.emoteNames[0], self.emoteValues[0]
            )
        else:
            winnerText = "Both emotes drew on {} votes!".format(self.emoteValues[0])

        self.bot.say("The voting has ended! {}".format(winnerText))
        self.bot.websocket_manager.emit("emotecounter_close")
        HandlerManager.remove_handler("on_message", self.on_message)
        self.votedUsers = []
        self.emoteNames = []
        self.emoteValues = [0, 0]
        self.votingOpen = False

    def on_message(self, source, message, whisper, **rest):
        if source.username_raw in self.votedUsers or whisper:
            return False

        cleanMessage = unidecode(message).strip()
        if cleanMessage == self.emoteNames[0]:
            self.emoteValues[0] += 1
        elif cleanMessage == self.emoteNames[1]:
            self.emoteValues[1] += 1
        else:
            return False

        self.votedUsers.append(source.username_raw)
        self.bot.websocket_manager.emit(
            "emotecounter_update", {"value1": self.emoteValues[0], "value2": self.emoteValues[1]}
        )

    def load_commands(self, **options):
        self.commands["emotecounter"] = Command.raw_command(
            self.emote_counter,
            description="Start displaying an emote counter on the CLR overlay",
            level=1500,
            examples=[
                CommandExample(
                    None,
                    "Display TriHard and Kappa for 30 seconds.",
                    chat="user:!emotecounter TriHard Kappa 30\n"
                    "bot:It's time to start voting for TriHard or Kappa! You only get one vote.",
                    description="",
                ).parse()
            ],
        )
        self.commands["stopcounter"] = Command.raw_command(
            self.cleanup_counter, description="Stop the ongoing emote counter", level=1500
        )

    def enable(self, bot):
        self.bot = bot
