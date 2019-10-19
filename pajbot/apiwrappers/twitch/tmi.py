from pajbot.apiwrappers.base import BaseAPI


class TwitchTMIAPI(BaseAPI):
    def __init__(self):
        super().__init__(base_url="https://tmi.twitch.tv/")

    def get_chatter_logins_by_login(self, login):
        response = self.get(["group", "user", login, "chatters"])

        all_chatters = []
        for chatter_category in response["chatters"].values():
            all_chatters.extend(chatter_category)

        return all_chatters
