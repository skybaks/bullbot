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
        self.add_command("bytier", self._get_users_by_tier)
        self.settings = None
        self.redis = redis
        self.thread = None
        self.private_loop = asyncio.get_event_loop()
        self.discord_task = self.schedule_task_periodically(300, self.check_discord_roles)
        queued_subs = self.redis.get("queued-subs-discord")
        unlinkinfo = self.redis.get("unlinks-subs-discord")
        if unlinkinfo is None or "array" in json.loads(unlinkinfo):
            data = {}
            self.redis.set("unlinks-subs-discord", json.dumps(data))
        if queued_subs is None or "array" in json.loads(queued_subs):
            data = {}
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

    async def _get_users_by_tier(self, message):
        if self.guild:
            with DBManager.create_session_scope() as db_session:
                admin_role = self.guild.get_role(int(self.settings["admin_role"]))
                if admin_role in message.author.roles:
                    args = message.content.split(" ")[1:]
                    if len(args) > 0:
                        requested_tier = args[0]
                        try:
                            requested_tier = int(requested_tier)
                        except:
                            return
                        return_message = ""
                        all_users_con = UserConnections._by_tier(db_session, requested_tier)
                        for user_con in all_users_con:
                            user = user_con.twitch_user
                            if user.tier is None:
                                tier = 0
                            elif user.tier >= 1:
                                tier = user.tier
                            else:
                                tier = 0
                            discord = self.get_discord_string(user_con.discord_user_id)
                            return_message += f"\nTwitch: {user} (<https://twitch.tv/{user.login}>){discord}\nSteam: <https://steamcommunity.com/profiles/{user_con.steam_id}>\n\n"
                        await self.private_message(
                            message.author,
                            f"All tier {requested_tier} subs:\n" + return_message + ("There are none!" if return_message == "" else ""),
                        )

    def get_discord_string(self, id):
        id = int(id)
        member = self.guild.get_member(id) or self.client.get_user(id)
        return (
            f"\nDiscord: {member.display_name}#{member.discriminator} (<https://discordapp.com/users/{member.id}>)"
            if member
            else ""
        )

    async def _connections(self, message):
        if self.guild:
            with DBManager.create_session_scope() as db_session:
                userconnections = None
                admin_role = self.guild.get_role(int(self.settings["admin_role"]))
                if admin_role in message.author.roles:
                    args = message.content.split(" ")[1:]
                    if len(args) > 0:
                        check_user = args[0]
                        user = User.find_by_user_input(db_session, check_user)
                        if user:
                            userconnections = (
                                db_session.query(UserConnections).filter_by(twitch_id=user.id).one_or_none()
                            )
                        if not userconnections:
                            await self.private_message(message.author, f"Connection data not found for user " + args[0])
                            return
                if not userconnections:
                    userconnections = (
                        db_session.query(UserConnections).filter_by(discord_user_id=str(message.author.id)).one_or_none()
                    )
                if not userconnections:
                    await self.private_message(
                        message.author,
                        f"You have not set up your account info yet, go to https://{self.bot.bot_domain}/connections to pair your twitch and steam to your discord account!",
                    )
                    return
                user = userconnections.twitch_user
                if user.tier is None:
                    tier = 0
                elif user.tier >= 1:
                    tier = user.tier
                else:
                    tier = 0
                discord = self.get_discord_string(userconnections.discord_user_id)
                await self.private_message(
                    message.author,
                    f"Tier {tier} sub:\nTwitch: {user} (<https://twitch.tv/{user.login}>){discord}\nSteam: <https://steamcommunity.com/profiles/{userconnections.steam_id}>",
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
            roles_allocated = {
                "twitch_sub_role": twitch_sub_role,
                "tier2_role": tier2_role,
                "tier3_role": tier3_role,
                "notify_role": notify_role,
                "ignore_role": ignore_role,
            }
            if twitch_sub_role is None:
                return
            quick_dict = {}
            with DBManager.create_session_scope() as db_session:
                all_connections = db_session.query(UserConnections).all()
                for connection in all_connections:
                    user_linked = User.find_by_id(db_session, connection.twitch_id)
                    member = self.guild.get_member(int(connection.discord_user_id))
                    if not user_linked or (
                        not member and not self.client.get_client(connection.discord_user_id)
                    ):  # Discord doesnt exist or Somehow the twitch doesnt exist in our database so we prune
                        connection._remove(db_session)
                        continue
                    quick_dict[connection.twitch_id] = connection
                    if not connection.twitch_login:
                        connection._update_twitch_login(db_session, user_linked.login)
                    if connection.twitch_login != user_linked.login:
                        if connection.tier > 1:
                            for member_to_notify in notify_role.members:
                                message = "Twitch login changed for a tier {tier} sub\nSteam: <https://steamcommunity.com/profiles/{steam_id}>\nOld Twitch: {old}\nNew Twitch: {new}"
                                if (
                                    self.settings["notify_on_name_change"]
                                    and connection.tier > 1
                                    and self.settings[f"notify_on_tier{connection.tier}"]
                                ):
                                    await self.private_message(
                                        member_to_notify,
                                        message.format(
                                            tier=connection.tier,
                                            steam_id=connection.steam_id,
                                            old=connection.twitch_login,
                                            new=user_linked.login,
                                        ),
                                    )
                            connection._update_twitch_login(db_session, user_linked.login)
                    if member and member.display_name + "#" + member.discriminator != connection.discord_username:
                        connection._update_discord_username(
                            db_session, member.display_name + "#" + member.discriminator
                        )
                queued_subs = json.loads(self.redis.get("queued-subs-discord"))
                unlinkinfo = json.loads(self.redis.get("unlinks-subs-discord"))
                for twitch_id in unlinkinfo:
                    unlinks = unlinkinfo[twitch_id]
                    member = self.guild.get_member(int(unlinks["discord_user_id"]))
                    if member:
                        if tier3_role is not None and tier3_role in member.roles:
                            await self.remove_role(member, tier3_role)
                        if tier2_role is not None and tier2_role in member.roles:
                            await self.remove_role(member, tier2_role)
                    user = User.find_by_id(db_session, twitch_id)
                    steam_id = unlinks["steam_id"]
                    discord = self.get_discord_string(unlinks["discord_user_id"])
                    tier = unlinks["discord_tier"]
                    message = "Account Data Unlinked: Tier {tier} sub removal notification:\nTwitch: {user} (<https://twitch.tv/{user.login}>){discord}\nSteam: <https://steamcommunity.com/profiles/{steam_id}>"
                    for member_to_notify in notify_role.members:
                        if self.settings["notify_on_unsub"] and tier > 1 and self.settings[f"notify_on_tier{tier}"]:
                            await self.private_message(
                                member_to_notify,
                                message.format(tier=tier, user=user, discord=discord, steam_id=steam_id),
                            )
                subs_to_return = {}
                if not self.settings["pause_bot"]:
                    for sub in queued_subs:  # sub "twitch_id" : date_to_be_removed
                        connection = quick_dict[sub]
                        time = queued_subs[sub]
                        user = connection.twitch_user
                        if not user:  # Idk how this happened but user isnt in our database purging
                            connection._remove(db_session)
                            continue
                        if user.tier == connection.tier or (not user.tier and connection.tier == 0):  # they resubbed before grace ended
                            continue
                        if ":" in time[-5:]:
                            time = f"{time[:-5]}{time[-5:-3]}{time[-2:]}"
                        if datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f%z") < utils.now():  # must be run now
                            member = self.guild.get_member(int(connection.discord_user_id))
                            if connection.tier > 1:
                                role = roles_allocated[f"tier{connection.tier}_role"]
                                if member and role and role in member.roles:
                                    await self.remove_role(member, role)
                                steam_id = connection.steam_id
                                discord = self.get_discord_string(connection.discord_user_id)
                                message = "Tier {tier} sub removal notification:\nTwitch: {user} (<https://twitch.tv/{user.login}>){discord}\nSteam: <https://steamcommunity.com/profiles/{steam_id}>"
                                if (
                                    self.settings["notify_on_unsub"]
                                    and connection.tier > 1
                                    and self.settings[f"notify_on_tier{connection.tier}"]
                                ):
                                    for member_to_notify in notify_role.members:
                                        await self.private_message(
                                            member_to_notify,
                                            message.format(
                                                tier=connection.tier, user=user, discord=discord, steam_id=steam_id
                                            ),
                                        )
                            if not user.tier or user.tier < 2 or not member or twitch_sub_role not in memeber.roles:
                                connection._update_tier(db_session, user.tier)
                        else:
                            subs_to_return[sub] = queued_subs[sub]
                    for member in twitch_sub_role.members:
                        if ignore_role is None or ignore_role not in member.roles:
                            connection = UserConnections._from_discord_id(db_session, str(member.id))
                            if not connection:
                                continue
                            discord = self.get_discord_string(connection.discord_user_id)
                            user = connection.twitch_user
                            if user.tier < 2:
                                continue
                            role = roles_allocated[f"tier{user.tier}_role"]
                            if not role:
                                continue
                            if user.tier == connection.tier:
                                if role not in member.roles:
                                    await self.add_role(member, role)
                                continue
                            steam_id = connection.steam_id
                            if connection.tier > 1:
                                if (
                                    self.settings["notify_on_unsub"]
                                    and connection.tier > 1
                                    and self.settings[f"notify_on_tier{connection.tier}"]
                                ):
                                    message = "Tier {tier} sub removal notification:\nTwitch: {user} (<https://twitch.tv/{user.login}>){discord}\nSteam: <https://steamcommunity.com/profiles/{steam_id}>"
                                    for member_to_notify in notify_role.members:
                                        await self.private_message(
                                            member_to_notify,
                                            message.format(
                                                tier=connection.tier, user=user, discord=discord, steam_id=steam_id
                                            ),
                                        )
                            if (
                                self.settings["notify_on_new_sub"]
                                and user.tier > 1
                                and self.settings[f"notify_on_tier{user.tier}"]
                            ):
                                message = "Tier {tier} sub notification:\nTwitch: {user} (<https://twitch.tv/{user.login}>){discord}\nSteam: <https://steamcommunity.com/profiles/{steam_id}>"
                                for member_to_notify in notify_role.members:
                                    await self.private_message(
                                        member_to_notify,
                                        message.format(tier=user.tier, user=user, discord=discord, steam_id=steam_id),
                                    )
                            connection._update_tier(db_session, user.tier)
                            await self.add_role(member, role)

            with DBManager.create_session_scope() as db_session:
                if not self.settings["pause_bot"]:
                    for user_connection in db_session.query(UserConnections).all():
                        if user_connection.twitch_id not in subs_to_return:
                            if user_connection.twitch_user.tier != user_connection.tier and not (not user_connection.twitch_user.tier and user_connection.tier == 0):
                                subs_to_return[user_connection.twitch_id] = str(
                                    utils.now() + timedelta(days=int(self.settings["grace_time"]))
                                )
                for tier in range(2, 4):
                    role = roles_allocated[f"tier{tier}_role"]
                    if role is not None:
                        for member in role.members:
                            if ignore_role is None or ignore_role not in member.roles:
                                connection = UserConnections._from_discord_id(db_session, str(member.id))
                                if not connection:
                                    await self.remove_role(member, role)
                                elif connection.tier == tier:
                                    continue
                                elif connection.twitch_id not in subs_to_return:
                                    if connection.tier != 0:
                                        await self.remove_role(member, role)
                                    else:
                                        if not self.settings["pause_bot"]:
                                            subs_to_return[connection.twitch_id] = str(
                                                utils.now() + timedelta(days=int(self.settings["grace_time"]))
                                            )
            self.redis.set("queued-subs-discord", json.dumps(subs_to_return))
            self.redis.set("unlinks-subs-discord", json.dumps({}))

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
