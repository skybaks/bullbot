import logging
from datetime import datetime
from datetime import timedelta

from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.longtimeout import LongTimeout
from pajbot.modules import BaseModule

log = logging.getLogger(__name__)


class LongTimeoutModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Long Timeout"
    DESCRIPTION = "Do an extra-long timeout"
    CATEGORY = "Feature"

    def __init__(self, bot):
        super().__init__(bot)
        self.checkJob = ScheduleManager.execute_every(30, self.check_retimeout)
        self.checkJob.pause()
        self.mysqlFormat = "%Y-%m-%d %H:%M:%S"

    def check_retimeout(self):
        with DBManager.create_session_scope() as session:
            timeoutList = session.query(LongTimeout).all()
            timeNow = datetime.now()
            for timeoutItem in timeoutList:
                # log.debug(timeoutItem.__dict__)
                timeoutEnd = timeoutItem.timeout_recent_end
                overallStart = timeoutItem.timeout_start
                overallEnd = timeoutItem.timeout_end

                if timeNow > overallEnd:
                    self.bot.whisper(
                        timeoutItem.timeout_author,
                        "{}'s timeout of {} hours has ended.".format(
                            timeoutItem.username, round((overallEnd - overallStart).seconds / 3600, 2)
                        ),
                    )
                    session.delete(timeoutItem)
                    continue

                if timeoutEnd < timeNow:
                    timeoutDuration = 1209600
                    if (overallEnd - timeNow).days < 14:
                        timeoutDuration = (overallEnd - timeNow).seconds

                    timeoutHours = round(float(timeoutDuration / 3600), 2)
                    timeoutItem.timeout_recent_end = (timeNow + timedelta(seconds=timeoutDuration)).strftime(
                        self.mysqlFormat
                    )
                    self.bot.whisper(
                        timeoutItem.timeout_author,
                        "Timing out {} for an additional {} hours".format(timeoutItem.username, timeoutHours),
                    )
                    self.bot._timeout(
                        timeoutItem.username,
                        timeoutDuration,
                        "Timed out {} for an additional {} hours, per {}'s !longtimeout".format(
                            timeoutItem.username, timeoutHours, timeoutItem.timeout_author
                        ),
                    )
                    session.add(timeoutItem)

    def long_timeout(self, **options):
        bot = options["bot"]
        message = options["message"]
        source = options["source"]
        errorString = "Invalid usage. !longtimeout user days"
        daysDuration = 0

        if not message or len(message.split(" ")) < 2:
            bot.whisper(source.username, errorString)
            return False

        splitMsg = message.split(" ")

        try:
            daysDuration = int(splitMsg[1])
            timeoutDuration = daysDuration * 86400
            if timeoutDuration > 1209600:
                timeoutDuration = 1209600

            nowTime = datetime.now()
            nowFormatted = nowTime.strftime(self.mysqlFormat)
            endTime = nowTime + timedelta(days=daysDuration)
            endFormatted = endTime.strftime(self.mysqlFormat)
            with bot.users.find_context(splitMsg[0]) as badPerson:
                if not badPerson:
                    bot.whisper(source.username, 'User "{}" doesn\'t exist in the database'.format(splitMsg[0]))
                    return False

                if badPerson.moderator:
                    bot.whisper(source.username, "You can't timeout mods")
                    return False

                if badPerson.level >= 420:
                    bot.whisper(
                        source.username, "{}'s level is too high, you can't time them out.".format(badPerson.username)
                    )
                    return False

                with DBManager.create_session_scope() as session:
                    if session.query(LongTimeout).filter(LongTimeout.username == badPerson.username).count() != 0:
                        bot.whisper(source.username, "{} already exists in the database".format(badPerson.username))
                        return False

                    longtimeout = LongTimeout(
                        username=badPerson.username,
                        timeout_start=nowFormatted,
                        timeout_end=endFormatted,
                        timeout_author=source.username,
                    )

                    session.add(longtimeout)

                    bot._timeout(
                        badPerson.username,
                        timeoutDuration,
                        "Timed out by {} for {} days total".format(source.username, daysDuration),
                    )
                    bot.whisper(
                        source.username, "Timed out {} for 14 days, per your !longtimeout".format(badPerson.username)
                    )

        except ValueError:
            bot.whisper(source.username, errorString)
            return False
        except Exception as e:
            log.error(e)

    def list_timeouts(self, **options):
        bot = options["bot"]
        source = options["source"]

        with DBManager.create_session_scope() as session:
            timeoutList = session.query(LongTimeout).all()

            if not timeoutList:
                bot.whisper(source.username, "There are currently no long timeouts.")
                return True

            listString = ""
            for timeoutItem in timeoutList:
                # log.debug(timeoutItem.__dict__)
                listString += "{}: {}, ".format(
                    timeoutItem.username, datetime.strftime(timeoutItem.timeout_end, self.mysqlFormat)
                )

            bot.whisper(source.username, listString[:-2])

    def remove_timeout(self, **options):
        bot = options["bot"]
        message = options["message"]
        source = options["source"]

        if not message:
            bot.whisper(source.username, "Invalid usage. !removetimeout user")
            return False

        with DBManager.create_session_scope() as session:
            remTimeout = session.query(LongTimeout).filter_by(username=message.split()[0]).one_or_none()
            if not remTimeout:
                bot.whisper(source.username, "User doesn't exist. See !listtimeouts")
                return False

            bot.whisper(
                source.username,
                "{}'s timeout of {} days has been cancelled.".format(
                    remTimeout.username, (remTimeout.timeout_end - remTimeout.timeout_start).days
                ),
            )
            session.delete(remTimeout)

    def load_commands(self, **options):
        from pajbot.models.command import Command
        from pajbot.models.command import CommandExample

        self.commands["longtimeout"] = Command.raw_command(
            self.long_timeout,
            level=500,
            description="Timeout someone for a duration longer than Twitch allows",
            can_execute_with_whispers=True,
            examples=[
                CommandExample(
                    None,
                    "Timeout syndereN for three weeks",
                    chat="user:!longtimeout synderen 21\n" "bot>user:Timed out syndereN for 21 days",
                ).parse()
            ],
        )

        self.commands["listtimeouts"] = Command.raw_command(
            self.list_timeouts,
            level=500,
            description="List pending timeouts",
            can_execute_with_whispers=True,
            examples=[
                CommandExample(
                    None,
                    "Get wben timeouts expire",
                    chat="user:!listtimeouts\n" "bot>user:syndereN: 2019-05-12 08:31:09",
                ).parse()
            ],
        )

        self.commands["removetimeout"] = Command.raw_command(
            self.remove_timeout,
            level=500,
            description="Remove unfulfilled timeout",
            can_execute_with_whispers=True,
            examples=[
                CommandExample(
                    None,
                    "Cancel syndereN's long timeout",
                    chat="user:!removetimeout syndereN\n" "bot>user:Successfully cancelled syndereN's 14 day timeout",
                ).parse()
            ],
        )

    def enable(self, bot):
        if bot:
            self.checkJob.resume()

    def disable(self, bot):
        if bot:
            self.checkJob.pause()
