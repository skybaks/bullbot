import logging
import threading

from pajbot import utils
from pajbot.exc import InvalidPointAmount
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.bet import BetGame
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
import asyncio

log = logging.getLogger(__name__)

class DiscordModule(BaseModule):
    AUTHOR = "TroyDota"
    ID = __name__.split(".")[-1]
    NAME = "Discord Module"
    DESCRIPTION = "Makes discord bot work :)"
    CATEGORY = "Feature"

    SETTINGS = [
        ModuleSetting(
            key="discord_token", 
            label="Token for discord bot",
            type="text", 
            placeholder="", 
            default=""
        ),
        ModuleSetting(
            key="discord_guild",
            label="Name of discord server", 
            type="text", 
            placeholder="", 
            default=""
        ),
        ModuleSetting(
            key="twitchsubrole", 
            label="Role given to twitch subs", 
            type="text", 
            placeholder="", 
            default=""
        ),
        ModuleSetting(
            key="tier2role", 
            label="Role given to tier 2 subs", 
            type="text", 
            placeholder="", 
            default=""
        ),
        ModuleSetting(
            key="tier3role", 
            label="Role given to tier 3 subs", 
            type="text", 
            placeholder="", 
            default=""
        ),
        ModuleSetting(
            key="role_to_notify", 
            label="Role to notify", 
            type="text", 
            placeholder="", 
            default=""
        ),
        ModuleSetting(
            key="admin_role", 
            label="Role of Admin", 
            type="text", 
            placeholder="", 
            default=""
        ),
        ModuleSetting(
            key="ignore_role", 
            label="Role of users to ignore", 
            type="text", 
            placeholder="", 
            default=""
        ),
        ModuleSetting(
            key="grace_time", 
            label="Time after unsub that the discord roles are not changed in days", 
            type="number", 
            placeholder="", 
            default="7"
        ),
        ModuleSetting(
            key="notify_on_unsub", 
            label="Sends a message to users mentioned upon an unsub", 
            type="boolean", 
            placeholder="", 
            default=True
        ),
        ModuleSetting(
            key="notify_on_new_sub", 
            label="Sends a message to role mentioned upon an new sub", 
            type="boolean", 
            placeholder="", 
            default=True
        ),
        ModuleSetting(
            key="notify_on_tier2", 
            label="Notify by tier 2", 
            type="boolean", 
            placeholder="", 
            default=False
        ),
        ModuleSetting(
            key="notify_on_tier3", 
            label="Notify by tier 3", 
            type="boolean", 
            placeholder="", 
            default=True
        ),
    ] 
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

    def enable(self, bot):
        if self.bot:
            log.info("Enabled Discord")
            self.bot.discord_bot_manager.configure(self.settings)

    def disable(self, bot):
        if self.bot:
            log.info("Disabled Discord")
            self.bot.discord_bot_manager.stop()
