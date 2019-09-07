from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.models.sniper import SniperLeaderboards
from pajbot.models.sniper import SniperSubmissions
from pajbot.web.utils import requires_level


def init(page):
    @page.route("/snipers/")
    @requires_level(420)
    def snipers(**options):
        with DBManager.create_session_scope() as session:
            sniperLeaderboard = session.query(SniperLeaderboards).all()
            sniperSubmissions = session.query(SniperSubmissions).all()

            return render_template(
                "admin/snipers.html", sniperLeaderboard=sniperLeaderboard, sniperSubmissions=sniperSubmissions
            )
