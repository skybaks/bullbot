import logging
from pajbot.managers.db import DBManager
from pajbot import utils
from pajbot.models.user_connection import UserConnections
from pajbot.models.user import User
import discord
import asyncio
import json
import threading
from datetime import datetime, timedelta

log = logging.getLogger("pajbot")


class Command(object):
    def __init__(self, name, handler, admin=False, args=""):  # --arg-req(name) --arg-opt(age)
        self.name = name
        self.admin = admin

        self.args = []

        if not asyncio.iscoroutinefunction(handler):
            handler = asyncio.coroutine(handler)
        self.handler = handler
        self.help = handler.__doc__ or ""

    def __str__(self):
        return "<Command {}: admin={}, args={}>".format(self.name, self.admin, len(self.args) > 0)

    async def call(self, message):
        await self.handler(message)


class CustomClient(discord.Client):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    async def on_ready(self):
        self.bot.guild = self.get_guild(int(self.bot.settings["discord_guild"]))
        if not self.bot.guild:
            log.error("Discord Guild not found!")
            return
        log.info(f"Discord Bot has started!")
        await self.bot.check_discord_roles()

    async def on_message(self, message):
        if not message.content.startswith("!"):
            return
        data = message.content.split("!")
        if len(data) <= 1:
            return
        cmd = self.bot.commands.get(data[1].split(" ")[0])
        if not cmd:
            return
        try:
            await cmd.call(message)
        except Exception as e:
            log.error(e)


class DiscordBotManager(object):
    def __init__(self, bot, redis):
        self.bot = bot
        self.client = CustomClient(self)
        self.commands = {}
        self.add_command("connections", self._connections)
        self.add_command("check", self._check)
        self.settings = None
        self.redis = redis
        self.thread = None
        self.private_loop = asyncio.get_event_loop()
        self.discord_task = self.schedule_task_periodically(300, self.check_discord_roles)
        queued_subs = self.redis.get("queued-subs-discord")
        unlinkinfo = self.redis.get("unlinks-subs-discord")
        if unlinkinfo is None:
            data = {"array": []}
            self.redis.set("unlinks-subs-discord", json.dumps(data))
        if queued_subs is None:
            data = {"array": []}
            self.redis.set("queued-subs-discord", json.dumps(data))

    def add_command(self, *args, **kwargs):
        cmd = Command(*args, **kwargs)
        self.commands[cmd.name] = cmd

    async def _check(self, message):
        if self.guild:
            admin_role = self.guild.get_role(int(self.settings["admin_role"]))
            if admin_role in self.guild.get_member(message.author.id).roles:
                await self.check_discord_roles()
                await self.private_message(message.author, f"Check Complete!")
                return

    async def _connections(self, message):
        if self.guild:
            with DBManager.create_session_scope() as db_session:
                userconnections = None
                author = self.guild.get_member(message.author.id)
                admin_role = self.guild.get_role(int(self.settings["admin_role"]))
                if admin_role in author.roles:
                    args = message.content.split(" ")[1:]
                    if len(args) > 0:
                        check_user = args[0]
                        user = User.find_by_user_input(db_session, check_user)
                        if user:
                            userconnections = (
                                db_session.query(UserConnections).filter_by(twitch_id=user.id).one_or_none()
                            )
                        if not userconnections:
                            await self.private_message(author, f"Connection data not found for user " + args[0])
                            return
                if not userconnections:
                    userconnections = (
                        db_session.query(UserConnections).filter_by(discord_user_id=str(author.id)).one_or_none()
                    )
                if not userconnections:
                    await self.private_message(
                        author,
                        f"You have not set up your account info yet, go to https://{self.bot.bot_domain}/connections to pair your twitch and steam to your discord account!",
                    )
                    return
                user = User.find_by_id(db_session, userconnections.twitch_id)
                if user.tier is None:
                    tier = 0
                elif user.tier >= 1:
                    tier = user.tier
                else:
                    tier = 0
                member = self.guild.get_member(int(userconnections.discord_user_id))
                await self.private_message(
                    message.author,
                    f"Tier {tier} sub:\nTwitch: {user} (<https://twitch.tv/{user.login}>) \nDiscord: {member.display_name}#{member.discriminator} (<https://discordapp.com/users/{member.id}>)\nSteam: <https://steamcommunity.com/profiles/{userconnections.steam_id}>",
                )

    async def private_message(self, member, message):
        message = discord.utils.escape_markdown(message)
        await self._private_message(member, message)

    async def remove_role(self, member, role):
        await self._remove_role(member, role)

    async def add_role(self, member, role):
        await self._add_role(member, role)

    async def _private_message(self, member, message):
        await member.create_dm()
        await member.dm_channel.send(message)

    async def _remove_role(self, member, role):
        await member.remove_roles(role)

    async def _add_role(self, member, role):
        await member.add_roles(role)

    async def check_discord_roles(self):
        if self.guild:
            twitch_sub_role = self.guild.get_role(int(self.settings["twitch_sub_role"]))
            tier2_role = self.guild.get_role(int(self.settings["tier2_role"]))
            tier3_role = self.guild.get_role(int(self.settings["tier3_role"]))
            notify_role = self.guild.get_role(int(self.settings["notify_role"]))
            ignore_role = self.guild.get_role(int(self.settings["ignore_role"]))
            quick_dict = {}
            with DBManager.create_session_scope() as db_session:
                all_connections = db_session.query(UserConnections).all()
                for connection in all_connections:
                    user_linked = User.find_by_id(db_session, connection.twitch_id)
                    quick_dict[connection.discord_user_id] = [
                        user_linked.tier,
                        connection,
                    ]
                    member = self.guild.get_member(int(connection.discord_user_id))
                    if not connection.twitch_login:
                        connection._update_twitch_login(db_session, user_linked.login)
                    if connection.twitch_login != user_linked.login:
                        twitch_name_changes.append([connection.twitch_login, connection.twitch_id])
                        if tier2_role is not None:
                            member_assigned_tier2 = tier2_role in member.roles
                        if tier3_role is not None:
                            member_assigned_tier3 = tier3_role in member.roles
                        for member_to_notify in notify_role.members:
                            user = User.find_by_id(db_session, unlinks["twitch_id"])
                            steam_id = unlinks["steam_id"]
                            message = "Twitch login changed for a tier {tier} sub\nSteam: <https://steamcommunity.com/profiles/{steam_id}>\nOld Twitch: {old}\nNew Twitch: {new}"
                            if self.settings["notify_on_name_change"]:
                                if member_assigned_tier3 and self.settings["notify_on_tier3"]:
                                    await self.private_message(
                                        member_to_notify,
                                        message.format(
                                            tier=3,
                                            steam_id=steam_id,
                                            old=connection.twitch_login,
                                            new=user_linked.login,
                                        ),
                                    )
                                if member_assigned_tier2 and self.settings["notify_on_tier2"]:
                                    await self.private_message(
                                        member_to_notify,
                                        message.format(
                                            tier=2,
                                            steam_id=steam_id,
                                            old=connection.twitch_login,
                                            new=user_linked.login,
                                        ),
                                    )
                        connection._update_twitch_login(db_session, user_linked.login)
                    if member and member.display_name + "#" + member.discriminator != connection.disord_username:
                        connection._update_disord_username(db_session, member.display_name + "#" + member.discriminator)
                queued_subs = json.loads(self.redis.get("queued-subs-discord"))["array"]
                unlinkinfo = json.loads(self.redis.get("unlinks-subs-discord"))["array"]
                for unlinks in unlinkinfo:
                    member = self.guild.get_member(int(unlinks["discord_user_id"]))
                    member_id = str(member.id)
                    if tier2_role is not None:
                        member_assigned_tier2 = tier2_role in member.roles
                    if tier3_role is not None:
                        member_assigned_tier3 = tier3_role in member.roles
                    if member_assigned_tier3 and tier3_role is not None:
                        await self.remove_role(member, tier3_role)
                    if member_assigned_tier2 and tier2_role is not None:
                        await self.remove_role(member, tier2_role)
                    for member_to_notify in notify_role.members:
                        user = User.find_by_id(db_session, unlinks["twitch_id"])
                        steam_id = unlinks["steam_id"]
                        message = "Account Data Unlinked: Tier {tier} sub removal notification:\nTwitch: {user} (<https://twitch.tv/{user.login}>)\nDiscord: {member.display_name}#{member.discriminator} (<https://discordapp.com/users/{member.id}>)\nSteam: <https://steamcommunity.com/profiles/{steam_id}>"
                        if self.settings["notify_on_unsub"]:
                            if member_assigned_tier3 and self.settings["notify_on_tier3"]:
                                await self.private_message(
                                    member_to_notify,
                                    message.format(tier=3, user=user, member=member, steam_id=steam_id),
                                )
                            if member_assigned_tier2 and self.settings["notify_on_tier2"]:
                                await self.private_message(
                                    member_to_notify,
                                    message.format(tier=2, user=user, member=member, steam_id=steam_id),
                                )
                subs_to_return = []
                if not self.settings["pause_bot"]:
                    for sub in queued_subs:  # sub [date_to_be_removed, member_id]
                        time = sub[0]
                        if ":" in time[-5:]:
                            time = f"{time[:-5]}{time[-5:-3]}{time[-2:]}"
                        if datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f%z") < utils.now():  # must be run now
                            member = self.guild.get_member(int(sub[1]))
                            member_id = str(member.id)
                            if tier2_role is not None:
                                member_assigned_tier2 = tier2_role in member.roles
                            if tier3_role is not None:
                                member_assigned_tier3 = tier3_role in member.roles
                            if quick_dict[member_id][0] == 2:
                                if member_assigned_tier3 and tier3_role is not None:
                                    await self.remove_role(member, tier3_role)
                            elif quick_dict[member_id][0] == 3:
                                if member_assigned_tier2 and tier2_role is not None:
                                    await self.remove_role(member, tier2_role)
                            else:
                                if member_assigned_tier2 and tier2_role is not None:
                                    await self.remove_role(member, tier2_role)
                                if member_assigned_tier3 and tier3_role is not None:
                                    await self.remove_role(member, tier3_role)
                            user = User.find_by_id(db_session, quick_dict[member_id][1].twitch_id)
                            steam_id = quick_dict[member_id][1].steam_id
                            message = "Tier {tier} sub removal notification:\nTwitch: {user} (<https://twitch.tv/{user.login}>)\nDiscord: {member.display_name}#{member.discriminator} (<https://discordapp.com/users/{member.id}>)\nSteam: <https://steamcommunity.com/profiles/{steam_id}>"
                            for member_to_notify in notify_role.members:
                                if self.settings["notify_on_unsub"]:
                                    if (
                                        member_assigned_tier3
                                        and quick_dict[member_id][0] != 3
                                        and self.settings["notify_on_tier3"]
                                    ):
                                        await self.private_message(
                                            member_to_notify,
                                            message.format(tier=3, user=user, member=member, steam_id=steam_id),
                                        )
                                    if (
                                        member_assigned_tier2
                                        and quick_dict[member_id][0] != 2
                                        and self.settings["notify_on_tier2"]
                                    ):
                                        await self.private_message(
                                            member_to_notify,
                                            message.format(tier=2, user=user, member=member, steam_id=steam_id),
                                        )
                        else:
                            subs_to_return.append(sub)
                if twitch_sub_role is None:
                    return
                for member in twitch_sub_role.members:
                    member_assigned_tier2 = tier2_role is not None and tier2_role in member.roles
                    member_assigned_tier3 = tier3_role is not None and tier3_role in member.roles
                    member_id = str(member.id)
                    if ignore_role is None or ignore_role not in member.roles:
                        if member_id in quick_dict:
                            message = "New tier {tier} sub notification:\nTwitch: {user} (<https://twitch.tv/{user.login}>)\nDiscord: {member.display_name}#{member.discriminator} (<https://discordapp.com/users/{member.id}>)\nSteam: <https://steamcommunity.com/profiles/{steam_id}>"
                            user = User.find_by_id(db_session, quick_dict[member_id][1].twitch_id)
                            steam_id = quick_dict[member_id][1].steam_id
                            for member_to_notify in notify_role.members:
                                if not member_assigned_tier3 and quick_dict[member_id][0] == 3:
                                    await self.add_role(member, tier3_role)
                                    if member_assigned_tier2:
                                        await self.remove_role(member, tier2_role)
                                    # notify role addition
                                    if self.settings["notify_on_new_sub"] and self.settings["notify_on_tier3"]:
                                        await self.private_message(
                                            member_to_notify,
                                            message.format(tier=3, user=user, member=member, steam_id=steam_id),
                                        )
                                elif not member_assigned_tier2 and quick_dict[member_id][0] == 2:
                                    await self.add_role(member, tier2_role)
                                    if member_assigned_tier3:
                                        await self.remove_role(member, tier3_role)
                                    # notify role addition
                                    if self.settings["notify_on_new_sub"] and self.settings["notify_on_tier2"]:
                                        await self.private_message(
                                            member_to_notify,
                                            message.format(tier=2, user=user, member=member, steam_id=steam_id),
                                        )
                            if (member_assigned_tier3 and quick_dict[member_id][0] != 3) or (
                                member_assigned_tier2 and quick_dict[member_id][0] != 2
                            ):
                                subs_to_return.append(
                                    [str(utils.now() + timedelta(days=int(self.settings["grace_time"]))), member_id]
                                )
                        else:
                            if member_assigned_tier2:
                                await self.remove_role(member, tier2_role)
                            if member_assigned_tier3:
                                await self.remove_role(member, tier3_role)
                if tier2_role is not None:
                    for member in tier2_role.members:
                        if ignore_role is None or ignore_role not in member.roles:
                            if twitch_sub_role not in member.roles or str(member.id) not in quick_dict:
                                await self.remove_role(member, tier2_role)
                if tier3_role is not None:
                    for member in tier3_role.members:
                        if ignore_role is None or ignore_role not in member.roles:
                            if twitch_sub_role not in member.roles or str(member.id) not in quick_dict:
                                await self.remove_role(member, tier3_role)
                data = {"array": subs_to_return}
                self.redis.set("queued-subs-discord", json.dumps(data))
                data = {"array": []}
                self.redis.set("unlinks-subs-discord", json.dumps(data))
                db_session.commit()

    async def run_periodically(self, wait_time, func, *args):
        while True:
            await asyncio.sleep(wait_time)
            if not self.client.is_closed():
                try:
                    await func(*args)
                except Exception as e:
                    log.error(e)

    def schedule_task_periodically(self, wait_time, func, *args):
        return self.private_loop.create_task(self.run_periodically(wait_time, func, *args))

    async def cancel_scheduled_task(self, task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def configure(self, settings):
        self.settings = settings
        self._start()

    def _start(self):
        if self.thread:
            self.private_loop.call_soon_threadsafe(self.private_loop.stop)
            self.thread.join()
            self.private_loop = asyncio.get_event_loop()
        self.private_loop.create_task(self.run())
        self.thread = threading.Thread(target=self.run_it_forever)
        self.thread.daemon = True
        self.thread.start()

    def run_it_forever(self):
        self.private_loop.run_forever()

    async def run(self):
        try:
            await self.client.start(self.bot.config["discord"]["discord_token"])
        except:
            pass

    def stop(self):
        self.private_loop.create_task(self._stop())

    async def _stop(self):
        log.info("Discord closing")
        await self.cancel_scheduled_task(self.discord_task)
        await self.client.logout()
        try:
            self.client.clear()
        except:
            pass
