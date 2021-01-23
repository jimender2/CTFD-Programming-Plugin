from __future__ import division  # Use floating point for math calculations

import math

from flask import Blueprint

from CTFd.models import Challenges, Solves, db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from CTFd.plugins.migrations import upgrade
from CTFd.utils.modes import get_model

import requests


class ProgrammingChallenges(Challenges):
    __mapper_args__ = {"polymorphic_identity": "dynamic"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    baseURL = db.Column(db.String, default="https://emkc.org/api/v1/piston/execute")
    language = db.Column(db.String, default="python3")
    stdin = db.Column(db.String, default="")
    args = db.Column(db.String, default="")

    def __init__(self, *args, **kwargs):
        super(ProgrammingChallenges, self).__init__(**kwargs)
        self.initial = kwargs["value"]


class ProgrammingChallenge(BaseChallenge):
    id = "Programming"  # Unique identifier used to register challenges
    name = "Programming"  # Name of a challenge type
    templates = (
        {  # Handlebars templates used for each aspect of challenge editing & viewing
            "create": "/plugins/CTFD-Programming-Plugin/assets/create.html",
            "update": "/plugins/CTFD-Programming-Plugin/assets/update.html",
            "view": "/plugins/CTFD-Programming-Plugin/assets/view.html",
        }
    )
    scripts = {  # Scripts that are loaded when a template is loaded
        "create": "/plugins/CTFD-Programming-Plugin/assets/create.js",
        "update": "/plugins/CTFD-Programming-Plugin/assets/update.js",
        "view": "/plugins/CTFD-Programming-Plugin/assets/view.js",
    }
    # Route at which files are accessible. This must be registered using register_plugin_assets_directory()
    route = "/plugins/CTFD-Programming-Plugin/assets/"
    # Blueprint used to access the static_folder directory.
    blueprint = Blueprint(
        "CTFD-Programming-Plugin",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )
    challenge_model = ProgrammingChallenges

    @staticmethod
    def create(request):
        """
        This method is used to process the challenge creation request.
        :param request:
        :return:
        """
        data = request.form or request.get_json()

        challenge = ProgrammingChallenges(**data)

        db.session.add(challenge)
        db.session.commit()

        return challenge

    @classmethod
    def read(cls, challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.

        :param challenge:
        :return: Challenge object, data dictionary to be returned to the user
        """
        challenge = ProgrammingChallenges.query.filter_by(id=challenge.id).first()
        data = {
            "id": challenge.id,
            "name": challenge.name,
            "value": challenge.value,
            "baseURL": challenge.baseURL,
            "language": challenge.language,
            "stdin": challenge.stdin,
            "args": challeng.args,
            "description": challenge.description,
            "category": challenge.category,
            "state": challenge.state,
            "max_attempts": challenge.max_attempts,
            "type": challenge.type,
            "type_data": {
                "id": cls.id,
                "name": cls.name,
                "templates": cls.templates,
                "scripts": cls.scripts,
            },
        }
        return data

    @classmethod
    def update(cls, challenge, request):
        """
        This method is used to update the information associated with a challenge. This should be kept strictly to the
        Challenges table and any child tables.

        :param challenge:
        :param request:
        :return:
        """
        data = request.form or request.get_json()

        for attr, value in data.items():
            # We need to set these to floats so that the next operations don't operate on strings
            if attr in ("initial", "minimum", "decay"):
                value = float(value)
            setattr(challenge, attr, value)

        return ProgrammingChallenge.calculate_value(challenge)

    @staticmethod
    def attempt(challenge, request):
        """
        This method is used to check whether a given input is right or wrong. It does not make any changes and should
        return a boolean for correctness and a string to be shown to the user. It is also in charge of parsing the
        user's input from the request itself.
        :param challenge: The Challenge object from the database
        :param request: The request the user submitted
        :return: (boolean, string)
        """
        data = request.form or request.get_json()
        # submission = data["submission"].strip()
        # instance_id = submission
        team_id = get_current_team().id

        try:
            r = requests.post(
                str(challenge.baseURL),
                json={
                    "language": challenge.language,
                    "source": data["submission"],
                    "stdin": "",
                    "args": [],
                },
            )
        except requests.exceptions.ConnectionError:
            return False, "Challenge oracle is not available. Talk to an admin."

        if r.status_code == 200:
            return True, "Correct"

        return False, "Incorrect"

        # flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        # for flag in flags:
        #    if get_flag_class(flag.type).compare(flag, submission):
        #        return True, 'Correct'
        # return False, 'Incorrect'

    @staticmethod
    def solve(user, team, challenge, request):
        """
        This method is used to insert Solves into the database in order to mark a challenge as solved.
        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        data = request.form or request.get_json()
        submission = "No flags for this challenge"
        solve = Solves(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(req=request),
            provided=submission,
        )
        db.session.add(solve)
        db.session.commit()
        db.session.close()

    @staticmethod
    def fail(user, team, challenge, request):
        """
        This method is used to insert Fails into the database in order to mark an answer incorrect.
        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        data = request.form or request.get_json()
        submission = "No flags for this challenge"
        wrong = Fails(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(request),
            provided=submission,
        )
        db.session.add(wrong)
        db.session.commit()
        db.session.close()


def load(app):
    upgrade()
    CHALLENGE_CLASSES["Programming"] = ProgrammingChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/CTFD-Programming-Plugin/assets/"
    )
