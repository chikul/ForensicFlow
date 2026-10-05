import json
from datetime import datetime, timezone, timedelta

from .user_base import UserBase
from .event_base import EventBase
from .artifact_base import ArtifactBase
from .rdf_export_base import RdfExportBase
from .device_base import DeviceBase

NEST_EVENTS_HISTORY_KEY = "structure_history."
NEST_USER_KEY = "user."
TZ_DELTA = 7200


EVENT_TYPES = {
    "0000": "INSTALLED",
    "0001": "MANUALTEST_COMPLETE",
    "0101": "PATHLIGHT", # Pathlight mode (glows in the darkness).
    "0102": "PROMISE", # Nightly Promise mode.
    "0103": "CHECK_IN", # Online status check?
    "0201": "POWER_OUTAGE",
    "0203": "DATA_MISSING",
    "0300": "BATTERY_OK",
    "0301": "BATTERY_LOW",
    "0302": "BATTERY_NEAR_CRITICAL",
    "0303": "BATTERY_CRITICAL",
    "0304": "PRODUCT_EXPIRED",
    "0305": "SMOKE_SENSOR_FAILURE",
    "0306": "CO_SENSOR_FAILURE",
    "0307": "LED_SENSOR_FAILURE",
    "0308": "TEMP_SENSOR_FAILURE",
    "0309": "ALS_FAILURE",
    "0310": "US_FAILURE",
    "0311": "PIR_FAILURE",
    "0401": "SMOKE_CLEAR",
    "0402": "SMOKE_HUSHED",
    "0403": "SMOKE_HEADS_UP",
    "0404": "SMOKE_EMERGENCY",
    "0501": "CO_CLEAR",
    "0502": "CO_HUSHED",
    "0503": "CO_HEADS_UP",
    "0504": "CO_EMERGENCY",
    "0701": "STEAM_DETECTED",
    "0800": "SOUNDCHECK_COMPLETE",
    "0801": "SOUNDCHECK_SPEAKER_OK",
    "0802": "SOUNDCHECK_SPEAKER_FAILURE",
    "0803": "SOUNDCHECK_BUZZER_OK",
    "0804": "SOUNDCHECK_BUZZER_FAILURE"
}

EVENTS_FILTER = [
    "0102", 
    "0103"
]


class NestRdfExport(RdfExportBase):
    def __init__(self, data_source: str, time_frame_start: datetime = None, time_frame_end: datetime = None):
        super().__init__(data_source, time_frame_start, time_frame_end)


    def carve(self):
        resulting_events = []
        resulting_devices = []
        resulting_artifacts = []
        resulting_users = []

        with open(self.data_sorce) as f:
            data = json.load(f)
            events = []
            user_name = ""
            email = ""
            
            for item in data:
                if NEST_EVENTS_HISTORY_KEY in item["object_key"]:
                    events += (item["value"]["events"])

                if NEST_USER_KEY in item["object_key"]:
                    user_name = item["value"]["name"]
                    email = item["value"]["email"]

            # Users.
            resulting_users.append(UserBase("NEST", user_name, source=self.data_sorce, hash=self.source_hash))

            # Artifacts.
            resulting_artifacts.append(ArtifactBase("Email", email, email, source=self.data_sorce, hash=self.source_hash))

            devices = []
            filtered = 0
            for event in events:
                if event["product"] not in devices:
                    devices.append(event["product"])
                    # NEST's own "product" field (e.g. "topaz.18B430...")
                    # already *is* the device's raw hardware serial -- id
                    # and hardware_id are the same value here, for parity
                    # with the other two extractors rather than because
                    # there's a separate friendly label to fall back to.
                    resulting_devices.append(DeviceBase("NEST", event["product"], source=self.data_sorce, hash=self.source_hash, hardware_id=event["product"]))

                if event['type'] not in EVENTS_FILTER:
                    end_time = datetime.fromtimestamp(event['end'] / 1000, tz=timezone(timedelta(seconds=TZ_DELTA))) if 'end' in event and event['start'] != event['end'] else None
                    start_time = datetime.fromtimestamp(event['start'] / 1000, tz=timezone(timedelta(seconds=TZ_DELTA)))
                    event_time = start_time
                    event_type = EVENT_TYPES[event["type"]] if event["type"] in EVENT_TYPES else f"Unknown ({event['type']})"
                    duration = (end_time - start_time).seconds if end_time is not None else 0

                    if start_time > self.time_frame_start and start_time < self.time_frame_end:
                        resulting_events.append(EventBase(event_time, "NEST", event_type, f"Duration {duration}s" if duration else "", device=resulting_devices[0], source=self.data_sorce, hash=self.source_hash))
                        filtered += 1

            # Interconnecting classes.
            resulting_users[0].events = resulting_events.copy()
            resulting_users[0].devices = resulting_devices.copy()
            resulting_users[0].artifacts = resulting_artifacts.copy()

            for i in range(len(resulting_devices)):
                resulting_devices[i].events = resulting_events.copy()
                resulting_devices[i].users = resulting_users.copy()
                resulting_devices[i].artifacts = resulting_artifacts.copy()

            for i in range(len(resulting_artifacts)):
                resulting_artifacts[i].events = resulting_events.copy()
                resulting_artifacts[i].users = resulting_users.copy()
                resulting_artifacts[i].devices = resulting_devices.copy()

            print(f"{'NEST Protect':30} Total events/filtered: {len(events)}/{filtered}")

        return (resulting_users, resulting_devices, resulting_events, resulting_artifacts)
