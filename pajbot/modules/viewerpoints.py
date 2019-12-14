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

    def command_masspoints(self, bot, source, message, **rest):
        if not message:
            return False

        pointsArgument = message.split(" ")[0]
        givePoints = 0

        try:
            givePoints = int(pointsArgument)
        except ValueError:
            bot.whisper(source, "Error: You must give an integer")
            return False

        currentChatters = bot.twitch_tmi_api.get_chatters_by_login(bot.streamer)
        numUsers = len(currentChatters)
        if not currentChatters:
            bot.say("Error fetching chatters")
            return False

        userBasics = bot.twitch_helix_api.bulk_get_user_basics_by_login(currentChatters)

        # Filtering
        userBasics = [e for e in userBasics if e is not None]

        with DBManager.create_session_scope() as db_session:
            # Convert to models
            userModels = [User.from_basics(db_session, e) for e in userBasics]

            for userModel in userModels:
                if userModel.num_lines < 5:
                    continue

                if userModel.subscriber:
                    userModel.points = userModel.points + givePoints * self.settings["sub_points"]
                else:
                    userModel.points = userModel.points + givePoints

        bot.say(f"{source} just gave {numUsers} viewers {givePoints} points each! Enjoy FeelsGoodMan")
