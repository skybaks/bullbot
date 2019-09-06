import argparse
import time

from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from pajbot.managers.db import DBManager
from pajbot.models.sniper import SniperLeaderboards
from pajbot.models.sniper import SniperSubmissions
from pajbot.web.utils import requires_level


def valid_date(arg):
    try:
        return time.strptime(arg, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise argparse.ArgumentTypeError("Not a valid date: '{}'.".format(arg))


class LeaderboardApi(Resource):
    @requires_level(420)
    def post(self, user_name, **options):
        post_parser = RequestParser()
        post_parser.add_argument(
            "recent_kill", type=valid_date, default=time.strftime("%Y-%m-%d %H:%M:%S"), required=False
        )
        post_parser.add_argument("kills", type=int, default=1, required=False)
        post_parser.add_argument("plusone", type=bool, default=False, required=False)

        args = post_parser.parse_args()

        recent_kill = args["recent_kill"]
        kills = args["kills"]

        with DBManager.create_session_scope() as db_session:
            sniperPosition = (
                db_session.query(SniperLeaderboards).filter(SniperLeaderboards.username == user_name).one_or_none()
            )

            if not sniperPosition:
                sniperPosition = SniperLeaderboards(username=user_name)

            if args["plusone"]:
                sniperPosition.kills = sniperPosition.kills + 1
            else:
                sniperPosition.kills = kills

            sniperPosition.recent_kill = recent_kill

            db_session.add(sniperPosition)

        return "OK", 200


class SubmissionApi(Resource):
    def put(self, user_name, **options):
        post_parser = RequestParser()
        post_parser.add_argument("link", required=True)

        args = post_parser.parse_args()

        link = args["link"]
        with DBManager.create_session_scope() as db_session:
            count = db_session.query(SniperSubmissions).filter(SniperSubmissions.link == link).count()

            if count > 0:
                return "Submission already exists in queue", 400

            newSubmission = SniperSubmissions(username=user_name, link=link)
            db_session.add(newSubmission)

        return "OK", 200

    @requires_level(420)
    def delete(self, user_name, **options):
        post_parser = RequestParser()
        post_parser.add_argument("link", required=True)

        args = post_parser.parse_args()

        link = args["link"]
        with DBManager.create_session_scope() as db_session:
            removeSubmission = (
                db_session.query(SniperSubmissions)
                .filter(SniperSubmissions.link == link and SniperSubmissions.user_name == user_name)
                .one_or_none()
            )

            if not removeSubmission:
                return "Submission not found in queue", 404

            db_session.delete(removeSubmission)

        return "OK", 200


def init(api):
    api.add_resource(LeaderboardApi, "/snipers/<user_name>")
    api.add_resource(SubmissionApi, "/snipers/<user_name>/submit")
