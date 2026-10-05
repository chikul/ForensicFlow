import sqlite3
from datetime import datetime

from .artifact_base import ArtifactBase
from .rdf_export_base import RdfExportBase
from .event_base import EventBase
from .user_base import UserBase
from .device_base import DeviceBase


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
    cursor.execute(f"SELECT customer_email, customer_name, customer_id FROM ACCOUNT WHERE authenticated = 'True'")
    rows = cursor.fetchall()

    if not rows:
        return None
    else:
        return [(x[1], x[0], x[2]) for x in rows]


def extract_device_serial(connection):
    cursor = connection.cursor()
    cursor.execute(f"SELECT device_serial_number FROM ALEXA_DEVICE WHERE device_family = 'VOX' LIMIT 1")
    row = cursor.fetchone()
    return row[0] if row else ""


def extract_events(connection):
    cursor = connection.cursor()
    cursor.execute(f"SELECT date, time, timezone, sourcetype, short, desc FROM TIMELINE")
    rows = cursor.fetchall()

    if not rows:
        return None
    else:
        result = []
        for row in rows:
            time_zone = row[2].replace("UTC", "")
            time_zone_sign = time_zone[0]
            time_zone = int(time_zone[1:])
            result.append((datetime.strptime(f"{row[0]} {row[1]} {time_zone_sign}{time_zone:02}00", '%Y-%m-%d %H:%M:%S.%f %z'), row[3], row[4], row[5]))

        return result


class AlexaRdfExport(RdfExportBase):
    def __init__(self, data_source: str, time_frame_start: datetime = None, time_frame_end: datetime = None):
        super().__init__(data_source, time_frame_start, time_frame_end)


    def carve(self):
        connection = create_connection(self.data_sorce)

        # Amazon devices.
        device_serial = extract_device_serial(connection)
        resulting_devices = [DeviceBase("Amazon", "Echo", source=self.data_sorce, hash=self.source_hash, hardware_id=device_serial)]

        # Amazon Users.
        resulting_users = []

        for user in extract_users(connection):
            resulting_users.append(UserBase("Amazon", user[0], source=self.data_sorce, hash=self.source_hash))

        # Artifacts.
        resulting_artifacts = []
        resulting_artifacts.append(ArtifactBase("Email", user[1], user[1], source=self.data_sorce, hash=self.source_hash))
        resulting_artifacts.append(ArtifactBase("Amazon:id", user[2], user[2], source=self.data_sorce, hash=self.source_hash))

        # Echo Events.
        resulting_events = []
        events = extract_events(connection)
        events.sort(key=lambda r: r[0])
        filtered = 0
        for event in events:
            if event[0] > self.time_frame_start and event[0] < self.time_frame_end:
                resulting_events.append(EventBase(event[0], "AmazonEcho", event[2], event[3], resulting_users[0], resulting_devices[0], resulting_artifacts, source=self.data_sorce, hash=self.source_hash, service=event[1]))
                filtered += 1

        # Interconnecting classes.
        resulting_users[0].events = resulting_events.copy()
        resulting_users[0].devices = resulting_devices.copy()
        resulting_users[0].artifacts = resulting_artifacts.copy()

        resulting_devices[0].events = resulting_events.copy()
        resulting_devices[0].users = resulting_users.copy()
        resulting_devices[0].artifacts = resulting_artifacts.copy()

        for i in range(len(resulting_artifacts)):
            resulting_artifacts[i].events = resulting_events.copy()
            resulting_artifacts[i].users = resulting_users.copy()
            resulting_artifacts[i].devices = resulting_devices.copy()
        
        print(f"{'Amazon Echo':30} Total events/filtered: {len(events)}/{filtered}")

        return (resulting_users, resulting_devices, resulting_events, resulting_artifacts)
