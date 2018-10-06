import requests
import json
import os

from dateutil import parser
from datetime import datetime, timezone
from collections import namedtuple

SECRETS_FILENAME = "SECRETS.json"
Friend = namedtuple('Friend', ['name', 'fbid', 'tid', 'in_squad'])


class AuthenticationError(Exception):
    """Yeah it's really important to write extremely enterprise well-documented hacky API code. Hacker News will love it I swear."""

class MoralityException(Exception):
    """It might come in handy later."""

class SquadError(Exception):
    """I have no excuse for this one."""


class NSASimulator:

    BASE_URL = "https://api.gotinder.com/"

    def __init__(self):
        self.sesh = requests.Session()
        # Look I have no idea what these are I just copy/pasted
        # them from the API call my phone makes. If this makes
        # you uncomfortable then you probably chill dude it's just bytes.
        self.headers = {
            # "User-Agent": "Tinder Android Version 5.2.0",
            # "Accept-Language": "en",
            # "If-None-Match": 'W/"1630244057"',
            "app-version": "1546",
            "os-version": "23",
            "platform": "android",
        }
        self._load_fb_auth()
        self.authed = False
        self.friends = {}
        self.profile_data = {}
        self.globals = None
        self.user = None
        self.versions = None

    def _load_fb_auth(self):
        if os.path.exists(SECRETS_FILENAME) and os.path.isfile(SECRETS_FILENAME):
                with open(SECRETS_FILENAME) as f:
                    self.fb_auth = json.load(f)
        else:
            raise AuthenticationError("Couldn't find {secrets_filename}. Did you create it and put your Facebook user id and auth token in it?".format(secrets_filename=SECRETS_FILENAME))

    def _auth(self):
        """
        You can only log in to Tinder with Facebook.

        This logs into Tinder with your supplied Facebook id and token,
        gets you a Tinder auth token which we're going to need for all our future API requests.

        This is only going to work if you already have a Tinder account
        connected to your Facebook account sorry fam.

        """
        # if "auth-token" in self.fb_auth:
        #     self.headers["X-Auth-Token"] = self.fb_auth["auth-token"]
        #     return
        print("Authenticating...")
        response = self.sesh.post(self.BASE_URL + "auth", data=self.fb_auth)
        if response.status_code == 200:
            print(response.text)
            r = response.json()
            self.headers["X-Auth-Token"] = r["token"]
            print("Authenticated to Tinder 🔒🔥")
            self.authed = True
            self.user = r["user"]
            self.globals = r["globals"]
            self.versions = r["versions"]
        else:
            raise AuthenticationError("Hey your Tinder auth didn't work. Did you put your Facebook user id and auth token into {secrets_filename}?".format(secrets_filename=SECRETS_FILENAME))

    def _get(self, url, **kwargs):
        if not self.authed:
            self._auth()
        print("Getting", url)
        response = self.sesh.get(self.BASE_URL + url, headers=self.headers, **kwargs)
        print(response.text)
        return response

    def _post(self, url, **kwargs):
        if not self.authed:
            self._auth()
        print("Posting to", url)
        response = self.sesh.post(self.BASE_URL + url, headers=self.headers, **kwargs)
        print(response.text)
        return response

    def get_facebook_friends_tinder_ids(self):

        if not os.path.exists(".creepyfile"):
            be_creepy = input("Sure you want to look at your Facebook friends' Tinder profiles? They might not like that. 🔒 [y/n]: ").lower() in ("y", "yes")

            if not be_creepy:
                raise MoralityException("😇 ")
            else:
                with open(".creepyfile", "w") as f:
                    f.write("😈")
                print("🔌🌐🔌")

        request = self._get("group/friends")
        if request.status_code != 200:
            raise SquadError("Couldn't get info about your friends. Is Tinder Social enabled on your account? Hint: If you're not in Australia it probably isn't.")

        friends = []
        friend_data = request.json()
        for result in friend_data["results"]:
            # Alright it's time for this json "parsing" fiesta.
            name = result["name"]
            tinder_id = result["user_id"]
            photos = result["photo"]
            sample_photo = photos[0]["processedFiles"][0]

            # Just pick any url to extract the Facebook ID from.
            sample_url = sample_photo["url"]
            facebook_id = sample_url.split("/")[3]

            friend = Friend(name, facebook_id, tinder_id, result["in_squad"])
            friends.append(friend)
            self.friends[facebook_id] = friend

        return friends

    def _get_profile(self, uid):
        if uid not in self.profile_data:
            self.profile_data[uid] = self._get("user/" + uid).json()["results"]
        return self.profile_data[uid]

    @classmethod
    def _datetimeise_profile(cls, profile_data):
        # Let's just put some smooth UX on that.
        extra_datums = {
            "ping_time": cls._to_local_time(profile_data["ping_time"]),
            "birth_date": cls._to_local_time(profile_data["birth_date"]),
            "join_time": datetime.fromtimestamp(int(profile_data["_id"][:8], 16)),
        }

        # I apologise for nothing.
        profile_data = profile_data.copy()
        profile_data.update(extra_datums)
        return profile_data

    def get_user(self, uid):
        profile_data = self._get_profile(uid)
        profile_data = self._datetimeise_profile(profile_data)
        return profile_data

    def get_profile(self, friend):
        profile_data = self.get_user(friend.tid)
        profile_data["full_name"] = friend.name
        return profile_data

    def get_interests(self):
        if not self.user:
            return {}
        return {p["id"]: p["name"] for p in self.user["interests"]}

    @staticmethod
    def _to_local_time(timestring):

        def utc_to_local(utc_dt):
            return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

        datetime_ = parser.parse(timestring)
        return utc_to_local(datetime_)

    def get_profiles(self):
        friends = self.get_facebook_friends_tinder_ids()
        return map(self.get_profile, friends)

    def get_recs(self):
        # return [self._datetimeise_profile(r) for r in self._get("recs").json()["results"]]
        return [self._datetimeise_profile(r.get("user", r)) for r in self._get("recs/core").json()["results"]]
