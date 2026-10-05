import sqlite3
from datetime import datetime, timezone, timedelta
from .rdf_export_base import RdfExportBase
from .event_base import EventBase
from .user_base import UserBase
from .device_base import DeviceBase


MICROSECONDS_FLAG = 1500000000000
TZ_DELTA = 7200


SENSOR_MAP = {
    "0006B4E5": "TheMotion (Motion Sensor)",
    "000A8540": "TheBouncer (Door Sensor)",
    "000A9474": "Unknown",
    "004D3209D9E4": "TheCube (CubeOne)"
}

SENSOR_ACTIONS_MAP = {
    "3": "Door Opened",
    "4": "Door Closed",
    "5": "Motion Detected"
}

TRANSLATABLE_SENSOR_IDS = {"0006B4E5", "000A8540"}


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    connection = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Exception as e:
        pass

    return connection


def extract_users(connection):
    cursor = connection.cursor()
    cursor.execute(f"SELECT operator FROM TB_IPUDairy WHERE operator <> '' GROUP BY operator")
    rows = cursor.fetchall()

    if not rows:
        return None
    else:
        return [x[0] for x in rows]

def extract_hub_ip(connection):
    cursor = connection.cursor()
    cursor.execute(f"SELECT Ip FROM TB_IPUVersionInfo WHERE Ip <> '0.0.0.0' LIMIT 1")
    row = cursor.fetchone()
    return row[0] if row else ""


def extract_actions(connection):
    cursor = connection.cursor()
    cursor.execute(f"SELECT profileid, profileName FROM TB_IPUDairy WHERE profileid <> '' GROUP BY profileid")
    rows = cursor.fetchall()

    if not rows:
        return None
    else:
        return {x[0]: x[1] for x in rows}

def extract_ipu_events(connection):
    cursor = connection.cursor()
    cursor.execute(f"SELECT date, operator, profileid FROM TB_IPUDairy WHERE profileid <> '' ORDER BY date ASC")
    rows = cursor.fetchall()

    if not rows:
        return None
    else:
        return [ (datetime.fromtimestamp(x[0] if x[0] < MICROSECONDS_FLAG else x[0] / 1000, tz=timezone(timedelta(seconds=TZ_DELTA))), x[1], x[2]) for x in rows ]

def extract_sensor_events(connection):
    cursor = connection.cursor()
    cursor.execute(f"SELECT date, operator, name, action, sensorID FROM TB_SensorDairy")
    rows = cursor.fetchall()

    if not rows:
        return None
    else:
        return [ (datetime.fromtimestamp(x[0] if x[0] < MICROSECONDS_FLAG else x[0] / 1000, tz=timezone(timedelta(seconds=TZ_DELTA))), x[1], x[2], x[3], x[4]) for x in rows ]


class IsaRdfExport(RdfExportBase):
    def __init__(self, data_source: str, time_frame_start: datetime = None, time_frame_end: datetime = None):
        super().__init__(data_source, time_frame_start, time_frame_end)


    def carve(self):
        connection = create_connection(self.data_sorce)
        hub_ip = extract_hub_ip(connection)

        # Sensors.
        resulting_devices = []
        for sensor_entry in SENSOR_MAP:
            sensor = SENSOR_MAP[sensor_entry]
            is_hub = sensor_entry == "004D3209D9E4"
            resulting_devices.append(DeviceBase(
                "iSmartAlarm", sensor, source=self.data_sorce, hash=self.source_hash,
                hardware_id=sensor_entry, observed_ip=hub_ip if is_hub else "",
            ))

        # ISA Users.
        resulting_users = []
        for user in extract_users(connection):
            resulting_users.append(UserBase("iSmartAlarm", user, source=self.data_sorce, hash=self.source_hash))

        resulting_events = []

        # IPU Events.
        filtered = 0
        ipu_events = extract_ipu_events(connection)
        actions_map = extract_actions(connection) or {}
        device = next((x for x in resulting_devices if x.id == "TheCube (CubeOne)"), None)
        for event in ipu_events:
            if event[0] > self.time_frame_start and event[0] < self.time_frame_end:
                user = next((x for x in resulting_users if x.name == event[1]), None)
                profile_id = event[2]
                # Falls back to the raw id itself if it's somehow missing
                # from the distinct profileid->profileName set gathered by
                # extract_actions()
                profile_name = actions_map.get(profile_id, profile_id)
                resulting_events.append(EventBase(event[0], "iSAHub", profile_name, user=user, device=device, source=self.data_sorce, hash=self.source_hash))
                filtered += 1

        print(f"{'iSmartAlarm Hub':30} Total events/filtered: {len(ipu_events)}/{filtered}")

        # Sensor Events.
        sensor_events = extract_sensor_events(connection)
        sensor_events.sort(key=lambda r: r[0])
        filtered = 0
        for event in sensor_events:
            if event[0] > self.time_frame_start and event[0] < self.time_frame_end:
                raw_action = event[3]
                if event[4] in TRANSLATABLE_SENSOR_IDS:
                    sensor_flag = SENSOR_ACTIONS_MAP.get(raw_action, f"Unmapped action {raw_action}")
                else:
                    sensor_flag = f"Unmapped action {raw_action}"
                sensor = SENSOR_MAP[event[4]]
                device = next((x for x in resulting_devices if x.id == sensor), None)
                resulting_events.append(EventBase(event[0], "iSASensor", sensor_flag, device=device, source=self.data_sorce, hash=self.source_hash))
                filtered += 1

        # Interconnecting classes.
        for i in range(len(resulting_devices)):
            device_events = [x for x in resulting_events if x.device.id == resulting_devices[i].id]
            resulting_devices[i].events = device_events

        for i in range(len(resulting_users)):
            user_events = [x for x in resulting_events if x.user and resulting_users[i].name == x.user.name]
            resulting_users[i].events = user_events
        
        print(f"{'iSmart Alarm Sensors':30} Total events/filtered: {len(sensor_events)}/{filtered}")

        return (resulting_users, resulting_devices, resulting_events, [])
