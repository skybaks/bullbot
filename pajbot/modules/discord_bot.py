import logging

from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class DiscordModule(BaseModule):
    AUTHOR = "TroyDota"
    ID = __name__.split(".")[-1]
    NAME = "Discord Module"
    DESCRIPTION = "Makes discord bot work :)"
    CATEGORY = "Feature"

    SETTINGS = [
        ModuleSetting(key="discord_guild", label="ID of discord server", type="text", placeholder="", default=""),
        ModuleSetting(
            key="twitch_sub_role", label="ID of role given to twitch subs", type="text", placeholder="", default=""
        ),
        ModuleSetting(
            key="tier2_role", label="ID of role given to tier 2 subs", type="text", placeholder="", default=""
        ),
        ModuleSetting(
            key="tier3_role", label="ID of role given to tier 3 subs", type="text", placeholder="", default=""
        ),
        ModuleSetting(key="notify_role", label="ID of role for notifications", type="text", placeholder="", default=""),
        ModuleSetting(key="admin_role", label="ID of role given to Admins", type="text", placeholder="", default=""),
        ModuleSetting(
            key="ignore_role", label="ID of role given to ignored users", type="text", placeholder="", default=""
        ),
        ModuleSetting(
            key="grace_time",
            label="Time after unsub that the discord roles are not purged in days",
            type="number",
            placeholder="",
            default="7",
        ),
        ModuleSetting(
            key="notify_on_unsub",
            label="Sends a message to users with notification role upon an unsub",
            type="boolean",
            placeholder="",
            default=True,
        ),
        ModuleSetting(
            key="notify_on_new_sub",
            label="Sends a message to users with notification role upon an new sub",
            type="boolean",
            placeholder="",
            default=True,
        ),
        ModuleSetting(
            key="pause_bot", label="Stop the bot from purging roles", type="boolean", placeholder="", default=False
        ),
        ModuleSetting(key="notify_on_tier2", label="Notify for tier 2", type="boolean", placeholder="", default=False),
        ModuleSetting(key="notify_on_tier3", label="Notify for tier 3", type="boolean", placeholder="", default=True),
    ]

    def enable(self, bot):
        if bot:
            log.info("Enabled Discord")
            self.bot.discord_bot_manager.configure(self.settings)

    def disable(self, bot):
        if bot:
            log.info("Disabled Discord")
            self.bot.discord_bot_manager.stop()
