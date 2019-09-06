import logging

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class CircleModule(BaseModule):
    AUTHOR = "DatGuy1"
    ID = __name__.split(".")[-1]
    NAME = "Circle"
    DESCRIPTION = "Make a circle!"
    CATEGORY = "Game"
    SETTINGS = [
            ModuleSetting(
                key="bad_phrases",
                label="If any of these bad phrases exist, stop. Seperate with |",
                type="text",
                default="admiralSleeper|admiralCringe"),

            ModuleSetting(
                key="circle_cost",
                label="Cost for command",
                type="number",
                required=True,
                placeholder="",
                default=100,
                constraints={
                    "min_value": 0,
                    "max_value": 1000,
                    }),
            ]

    def __init__(self, bot):
        super().__init__(bot)
        self.circleString = "repme2 repme2 ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ repme2 repme1 repme2 ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ repme2 repme2"
        self.pyramidString = "repme1 ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ repme1 repme1 ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ repme1 repme1 repme1 ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ repme1 repme1 repme1 repme1 ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ repme1 repme1 repme1 repme1 repme1"
        self.reversePyramid = "⠀ ⠀ ⠀ ⠀ ⠀ repme1 repme1 repme1 repme1 ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ repme1 repme1 repme1 ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ repme1 repme1 ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ repme1"

    def replace_say(self, sayString, bot, source):
        if any(badPhrase in sayString.split() for badPhrase in self.badPhrases):
            bot.whisper(source.username, "One or more of the replacements you chose are disallowed. Your points have been refunded.")
            return False

        if bot.is_bad_message(sayString):
            bot.whisper(source.username, "One or more of the replacements you chose are disallowed. Your points have been refunded.")
            return False
        else:
            bot.say(sayString)

    # TODO: Centralise to one function

    def command_pyramid(self, **options):
        bot = options["bot"]
        source = options["source"]
        message = options["message"]

        if not message:
            bot.whisper(source.username, "Invalid syntax. Usage: !pyramid word")
            return False

        splitMsg = message.split()
        sayString = self.pyramidString

        sayString = sayString.replace("repme1", splitMsg[0])
        self.replace_say(sayString, bot, source)

    def command_reverse(self, **options):
        bot = options["bot"]
        source = options["source"]
        message = options["message"]

        if not message:
            bot.whisper(source.username, "Invalid syntax. Usage: !reversepyramid word")
            return False

        splitMsg = message.split()
        sayString = self.reversePyramid

        sayString = sayString.replace("repme1", splitMsg[0])
        self.replace_say(sayString, bot, source)

    def command_circle(self, **options):
        bot = options["bot"]
        source = options["source"]
        message = options["message"]

        if not message:
            bot.whisper(source.username, "Invalid syntax. Usage: !circle emoteone emotetwo")
            return False

        splitMsg = message.split()
        sayString = self.circleString

        if len(splitMsg) == 1:
            sayString = sayString.replace("repme2", splitMsg[0])
            sayString = sayString.replace("repme1", splitMsg[0])
        else:
            sayString = sayString.replace("repme2", splitMsg[1])
            sayString = sayString.replace("repme1", splitMsg[0])

        self.replace_say(sayString, bot, source)

    def load_commands(self, **options):
        self.commands["circle"] = Command.raw_command(self.command_circle,
            level = 100,
            delay_all = 2,
            delay_user = 0,
            can_execute_with_whisper = False,
            cost = self.settings["circle_cost"],
            description="Generate a circle"
            )
        self.commands["pyramid"] = Command.raw_command(self.command_pyramid,
            level = 100,
            delay_all = 5,
            delay_user = 0,
            can_execute_with_whisper = False,
            cost = self.settings["circle_cost"],
            description="Generate a pyramid"
            )
        self.commands["reversepyramid"] = Command.raw_command(self.command_reverse,
            level = 100,
            delay_all = 5,
            delay_user = 0,
            can_execute_with_whisper = False,
            cost = self.settings["circle_cost"],
            description="Generate a reverse pyramid"
            )
        self.commands["pyr"] = self.commands["pyramid"]
        self.commands["reversepyr"] = self.commands["reversepyramid"]

    def enable(self, bot):
        self.badPhrases = self.settings["bad_phrases"].split("|")
