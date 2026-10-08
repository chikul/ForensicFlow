"""
KnownFactsExtractor: parses data/known_facts.yaml - investigator-supplied
ground truth from the scenario narrative (suspects, their known associates,
scene-observed devices with no extractable data source, and events with no
corresponding raw telemetry) - into the same UserBase/DeviceBase/EventBase/
ArtifactBase records every device-telemetry extractor produces.

Deliberately does NOT apply time_frame_start/time_frame_end filtering: these 
are facts asserted by the investigation itself, not timestamped device 
telemetry to be windowed to a time-of-interest.
"""
from datetime import datetime

import yaml

from .device_base import DeviceBase
from .event_base import EventBase
from .rdf_export_base import RdfExportBase
from .user_base import UserBase


class KnownFactsExtractor(RdfExportBase):
    def __init__(self, data_source: str, time_frame_start: datetime = None, time_frame_end: datetime = None):
        super().__init__(data_source, time_frame_start, time_frame_end)

    def carve(self):
        resulting_users = []
        resulting_devices = []
        resulting_events = []
        resulting_artifacts = []

        with open(self.data_sorce, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        users_by_name = {}
        for suspect in data.get("suspects", []):
            user = UserBase(
                "Suspect", suspect["name"],
                source=self.data_sorce, hash=self.source_hash,
                notes=suspect.get("notes", "").strip(),
                associates=[],  # Explicit fresh list per instance
            )
            users_by_name[suspect["name"]] = user
            resulting_users.append(user)

        for pair in data.get("associates", []):
            name_a, name_b = pair[0], pair[1]
            if name_a not in users_by_name or name_b not in users_by_name:
                raise ValueError(f"known_facts.yaml: associates pair {pair} references an undeclared suspect")
            users_by_name[name_a].associates.append(name_b)
            users_by_name[name_b].associates.append(name_a)

        for device in data.get("known_devices", []):
            resulting_devices.append(DeviceBase(
                device["type"], device["id"],
                source=self.data_sorce, hash=self.source_hash,
                notes=device.get("notes", "").strip(),
            ))

        for event in data.get("known_events", []):
            resulting_events.append(EventBase(
                datetime.fromisoformat(event["time"]), event["type"], event["subtype"],
                source=self.data_sorce, hash=self.source_hash,
            ))

        for user in resulting_users:
            user.events = resulting_events.copy()

        print(f"{'Known facts':30} suspects/associates/known_devices/known_events: "
              f"{len(resulting_users)}/{len(data.get('associates', []))}/{len(resulting_devices)}/{len(resulting_events)}")

        return (resulting_users, resulting_devices, resulting_events, resulting_artifacts)
