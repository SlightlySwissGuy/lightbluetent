from os import getenv
from urllib.parse import urlencode
from hashlib import sha1

import requests
import xmltodict

# Represents a meeting from an attendee's viewpoint.
# Usage is something like this (error handling omitted):
#
#   meeting = AttendeeMeeting("meeting1234", "password1234")
#   success, url = meeting.join("John Smith")
#   redirect to url

class AttendeeMeeting:

    def __init__(self, meeting_id, attendee_pw):
        self.meeting_id = meeting_id
        self.attendee_pw = attendee_pw
        self.bbb = BBB()


    # Join the meeting with a given full name.
    # Returns (True, "[join_url]") on success, (False, "[error_msg]") on failure.
    def join(self, full_name):
        params = {}
        params["fullName"] = full_name
        params["meetingID"] = self.meeting_id
        params["password"] = self.attendee_pw

        return self.bbb.join(params)


# Represents a meeting from moderator's viewpoint.
# Usage is something like this (error handling omitted):
#
#   meeting = ModeratorMeeting("My Meeting", "meeting1234", ... )
#
#   if not meeting.is_running():
#       success, message = meeting.create()
#
#   success, url = meeting.join("John Smith")
#   redirect to url
#   ...
#   when bored:
#       success, message = meeting.end()

class ModeratorMeeting:

    def __init__(self, meeting_name, meeting_id, attendee_pw, moderator_pw, \
            welcome_text, logo, banner_text, banner_color, mute_on_start, \
            disable_private_chat):

        # Boilerplate.
        self.meeting_name = meeting_name
        self.meeting_id = meeting_id
        self.attendee_pw = attendee_pw
        self.moderator_pw = moderator_pw
        self.welcome_text = welcome_text
        self.logo = logo
        self.banner_text = banner_text
        self.banner_color = banner_color
        self.mute_on_start = mute_on_start
        self.disable_private_chat = disable_private_chat

        # Create BBB.
        self.bbb = BBB()


    # Returns (True, "") on success, (False, "[error_msg]") on failure.
    def create(self):
        params = {}
        params["name"] = self.meeting_name
        params["meetingID"] = self.meeting_id
        params["attendeePW"] = self.attendee_pw
        params["moderatorPW"] = self.moderator_pw
        params["welcome"] = self.welcome_text
        params["logo"] = self.logo
        params["bannerText"] = self.banner_text
        params["bannerColor"] = self.banner_color
        params["muteOnStart"] = "true" if self.mute_on_start else "false"
        params["lockSettingsDisablePrivateChat"] = "true" if self.disable_private_chat else "false"

        return self.bbb.create(params)


    # Returns (True, "[join_url]") on success, (False, "[error_msg]") on failure.
    def join(self, full_name):
        params = {}
        params["fullName"] = full_name
        params["meetingID"] = self.meeting_id
        params["password"] = self.moderator_pw

        return self.bbb.join(params)


    # Returns (True, "") on success, (False, "[error_msg]") on failure.
    def end(self):
        params = {}
        params["meetingID"] = self.meeting_id
        params["password"] = self.moderator_pw

        return self.bbb.end(params)


    # Returns True if meeting is running,
    # False if meeting is not running or on error.
    def is_running(self):
        params = {}
        params["meetingID"] = self.meeting_id

        return self.bbb.is_meeting_running(params)


# Basic BBB API functions.
# Internal use only, not for individual resale.

class BBB:

    # Create a new call.
    # Returns (True, "") if successful, otherwise (False, "[error_message]").
    def create(self, params):
        created = False
        message = ""
        response = self.request("create", params)

        if "returncode" not in response or "message" not in response:
            created = False
            message = "Error: Malformed response from server."
        else:
            if response["returncode"] != "SUCCESS":
                created = False
                message = response["message"]
            else:
                created = True

        return (created, message)


    # Join a call.
    # Returns (True, "[call_url]") if successful, otherwise
    # (False, "[error_message]").
    def join(self, params):
        joined = False
        message = ""
        call_url = ""
        response = self.request("join", params)

        if "returncode" not in response or "message" not in response:
            joined = False
            message = "Error: Malformed response from server."
        else:
            message = response["message"]
            if response["returncode"] != "SUCCESS":
                joined = False
            else:
                joined = True
                call_url = response["url"]

        if joined:
            return (joined, call_url)
        else:
            return (joined, message)


    # End a meeting.
    # Returns (True, "") if successful, otherwise (False, "[error_message]").
    def end(self, params):
        ended = False
        message = ""
        response = self.request("end", params)

        if "returncode" not in response or "message" not in response:
            ended = False
            message = "Error: Malformed response from server."
        else:
            if response["returncode"] != "SUCCESS":
                ended = False
                message = response["message"]
            else:
                ended = True

        return (ended, message)


    # Check if a meeting is running (based on meetingID).
    # Returns true if the meeting is running, and false otherwise.
    # Any error causes a return value of False.
    def is_meeting_running(self, params):
        success = False
        running = False
        response = self.request("isMeetingRunning", params)

        if "returncode" not in response:
            success = False
        else:
            if response["returncode"] != "SUCCESS":
                success = False
            else:
                success = True
                if response["running"] == "true":
                    running = True

        return (success and running)


    def request(self, call, params):
        url = self.build_url(call, params)
        res = requests.get(url, timeout=(0.5, 10))
        xml = xmltodict.parse(res.text)

        return xml["response"]


    def generate_checksum(self, call, query):
        hash_string = call + query + getenv("BIGBLUEBUTTON_SECRET")
        checksum = sha1(hash_string.encode()).hexdigest()

        return checksum


    def build_url(self, call, params):
        query = urlencode(params or {})
        query += "&checksum=" + self.generate_checksum(call, query)
        url = f"{getenv('BIGBLUEBUTTON_URL')}{call}?{query}"

        return url
