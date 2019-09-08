import logging
import threading

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
            self.receive_events_thread._stop
        except:
            pass

        self.socketio = SocketIO("https://sockets.streamlabs.com", params={"token": settings["socket_token"]})
        self.socketio.on("event", self.on_event)
        self.socketio.on("disconnect", self.on_disconnect)

        self.receive_events_thread = threading.Thread(target=self._receive_events_thread)
        self.receive_events_thread.daemon = True
        self.receive_events_thread.start()

    def on_event(self, *args):
        DonationPointsModule.updatePoints(self.bot, self.settings, args)

    def on_disconnect(self, *args):
        log.error("Socket disconnected. Donations no longer monitored")
        ScheduleManager.execute_delayed(30, DonationPointsModule.restartClass)

    def _receive_events_thread(self):
        self.socketio.wait()


class DonationPointsModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Donate for points"
    DESCRIPTION = "Users can donate to receive points."
    ENABLED_DEFAULT = True
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(key="socket_token", label="Socket token", type="text", required=True),
        ModuleSetting(key="multiplynum", label="One usd equals how many points", type="number", required=True),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

    def enable(self, bot):
        self.socketClass = asyncSocketIO(self.bot, self.settings)

    def restartClass(self):
        del self.socketClass
        self.socketClass = asyncSocketIO(self.bot, self.settings)

    @staticmethod
    def updatePoints(bot, settings, args):
        if args[0]["type"] != "donation":
            return False

        if "historical" in args[0]["message"][0]:
            return False

        donation_name = args[0]["message"][0]["name"]

        user = bot.users.find(donation_name)
        if user is None:
            return False

        finalValue = int(float(args[0]["message"][0]["amount"]) * int(settings["multiplynum"]))

        user.points += finalValue
        user.save()

        self.bot.whisper(
            user.username, "You have been given {} points due to a donation in your name".format(finalValue)
        )
