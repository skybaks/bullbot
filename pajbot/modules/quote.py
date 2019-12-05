import logging
import re

import requests

from pajbot.models.command import Command
from pajbot.modules import BaseModule

log = logging.getLogger(__name__)


class QuoteModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Random quote"
    DESCRIPTION = "Some recent/random message stuff"
    CATEGORY = "Feature"

    def __init__(self, bot):
        super().__init__(bot)
        self.baseURL = "https://api.gempir.com/channel/admiralbulldog/user"

    def random_quote(self, **options):
        bot = options["bot"]
        source = options["source"]
        message = options["message"]

        if message is None or len(message) == 0:
            # The user did not supply any arguments
            return False

        msg_split = message.split(" ")
        if len(msg_split) < 1:
            # The user did not supply enough arguments
            bot.whisper(source.username, "Usage: !rq USERNAME")
            return False

        username = msg_split[0].lower()
        if len(username) < 2:
            # The username specified was too short. ;-)
            return False

        with bot.users.find_context(username) as target:
            while True:
                r = requests.get("{}/{}/random".format(self.baseURL, username))

                if target is None:
                    bot.say("This user does not exist FailFish")
                    return False

                if r.status_code != 200 or not r.text:
                    bot.say("Error with fetching website: {}".format(r.status_code))
                    return False

                if "{} was timed out for ".format(username) in r.text:
                    continue

                bot.say("{}: {}".format(username, r.text))
                break

    def last_quote(self, **options):
        bot = options["bot"]
        source = options["source"]
        message = options["message"]

        if message is None or len(message) == 0:
            # The user did not supply any arguments
            return False

        msg_split = message.split(" ")
        if len(msg_split) < 1:
            # The user did not supply enough arguments
            bot.whisper(source.username, "Usage: !lq USERNAME")
            return False

        username = msg_split[0].lower()
        if len(username) < 2:
            # The username specified was too short. ;-)
            return False

        with bot.users.find_context(username) as target:
            r = requests.get("{}/{}".format(self.baseURL, username))

            if target is None:
                bot.say("This user does not exist FailFish")
                return False

            if r.status_code != 200 or not r.text:
                bot.say("Error with fetching website: {}".format(r.status_code))
                return False

            recentMsg = r.text.splitlines()[-1]

            try:
                formatMsg = re.search(r"ldon (.*)", recentMsg).group(1)
            except AttributeError:
                bot.say("{} was most recently timed out.".format(username))

            if bot.is_bad_message(r.text):
                bot.say("{}'s recent message has a bad word :\\".format(username))
            else:
                bot.say("{}: {}".format(username, formatMsg))

    def load_commands(self, **options):
        self.commands["rq"] = Command.raw_command(self.random_quote, delay_all=2, delay_user=5)
        self.commands["randomquote"] = self.commands["rq"]
        self.commands["lastquote"] = Command.raw_command(self.last_quote, delay_all=2, delay_user=5)
        self.commands["lq"] = self.commands["lastquote"]
        self.commands["lastmessage"] = self.commands["lastquote"]
        self.commands["lastmessage"] = self.commands["lastquote"]
