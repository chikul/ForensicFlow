from datetime import datetime
import hashlib
import pytz


class RdfExportBase:
    def __init__(self, data_source: str, time_frame_start: datetime = None, time_frame_end: datetime = None):
        self.data_sorce: str = data_source
        self.time_frame_start: datetime = time_frame_start if time_frame_start else datetime.min.replace(tzinfo=pytz.UTC)
        self.time_frame_end: datetime = time_frame_end if time_frame_end else datetime.max.replace(tzinfo=pytz.UTC)
        self.source_hash = str(hashlib.md5(open(self.data_sorce, "rb").read()).hexdigest())


    def carve(self):
        pass
