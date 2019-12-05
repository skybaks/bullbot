import logging

from pajbot.managers.db import DBManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class MassPointsModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Mass Points"
    DESCRIPTION = "Give points to everyone watching the stream"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="sub_points",
            label="Points to give for subscribers for each pleb point",
            type="number",
            required=True,
            placeholder="1",
            default=1,
            constraints={"min_value": 0, "max_value": 100},
        )
    ]

    def __init__(self, bot):
        super().__init__(bot)

    def load_commands(self, **options):
        self.commands["masspoints"] = Command.raw_command(
            self.command_masspoints,
            level=500,
            description="Give a specific number of points to everyone watching the stream",
            examples=[
                CommandExample(
                    None,
                    "Give 300 points (for a fisting)",
                    chat="user:!masspoints 300\n" "bot: user just gave 159 viewers 300 points! Enjoy FeelsGoodMan",
                    description="Give 300 points to the number of people in chat, in this case 159",
                ).parse()
            ],
        )

    def command_masspoints(self, **options):
        bot = options["bot"]
        source = options["source"]
        message = options["message"]

        if not message:
            return False

        pointsArgument = message.split(" ")[0]
        givePoints = 0

        try:
            givePoints = int(pointsArgument)
        except ValueError:
            bot.whisper(source.username_raw, "Error: You must give an integer")
            return False

        currentChatters = bot.twitch_tmi_api.get_chatters(bot.streamer)
        numUsers = len(currentChatters)
        if not currentChatters:
            bot.say("Error fetching chatters")
            return False

        with DBManager.create_session_scope() as db_session:
            userModels = db_session.query(User).filter(User.login.in_(currentChatters), User.num_lines > 5)
            for userModel in userModels:
                if userModel.subscriber:
                    userModel.points += givePoints * self.settings["sub_points"]
                else:
                    userModel.points += givePoints

        bot.say(
            "{} just gave {} viewers {} points each! Enjoy FeelsGoodMan".format(
                source.username_raw, numUsers, givePoints
            )
        )
