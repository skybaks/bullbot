import logging
import threading

from currency_converter import CurrencyConverter
from socketIO_client_nexus import SocketIO

from pajbot.managers.schedule import ScheduleManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class asyncSocketIO:
    def __init__(self, bot, settings):
        self.bot = bot
        self.settings = settings

        try:
            self.receiveEventsThread._stop
        except:
            pass

        self.socketIO = SocketIO("https://sockets.streamlabs.com", params={"token": settings["socketToken"]})
        self.socketIO.on("event", self.onEvent)
        self.socketIO.on("disconnect", self.onDisconnect)

        self.receiveEventsThread = threading.Thread(target=self._receiveEventsThread)
        self.receiveEventsThread.daemon = True
        self.receiveEventsThread.start()

    def onEvent(self, *args):
        DonationPointsModule.updatePoints(self.settings["usdValue"], args)

    def onDisconnect(self, *args):
        log.error("Socket disconnected. Donations no longer monitored")
        ScheduleManager.execute_delayed(30, DonationPointsModule.restartClass)

    def _receiveEventsThread(self):
        self.socketIO.wait()


class DonationPointsModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Donate for points"
    DESCRIPTION = "Users can donate to receive points."
    ENABLED_DEFAULT = True
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(key="socketToken", label="Socket token", type="text", required=True),
        ModuleSetting(key="usdValue", label="1 USD equals how many points", type="number", required=True),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot
        self.currencyConverter = CurrencyConverter()

    def enable(self, bot):
        self.socketClass = asyncSocketIO(self.bot, self.settings)

    def restartClass(self):
        del self.socketClass
        self.socketClass = asyncSocketIO(self.bot, self.settings)

    def updatePoints(self, usdPoints, args):
        if args[0]["type"] != "donation":
            return False

        detailedArgs = args[0]["message"][0]

        if "historical" in detailedArgs:
            return False

        donationName = detailedArgs["name"]

        user = self.bot.users.find(donationName)
        if user is None:
            return False

        usdAmount = self.currencyConverter.convert(float(detailedArgs["amount"]), detailedArgs["currency"], "USD")

        finalValue = int(usdAmount * int(usdPoints))

        user.points += finalValue
        user.save()

        self.bot.whisper(
            user.username, "You have been given {} points due to a donation in your name".format(finalValue)
        )
