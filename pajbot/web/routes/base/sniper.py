from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.models.sniper import SniperLeaderboards


def init(app):
    @app.route("/snipers/")
    def user_snipers():
        with DBManager.create_session_scope() as session:
            snipers = session.query(SniperLeaderboards).all()

            return render_template(
                "snipers.html",
                snipers=snipers
            )
