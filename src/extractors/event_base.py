from datetime import datetime

from .user_base import UserBase
from .device_base import DeviceBase


class EventBase():
    def __init__(self, time: datetime = None, type: str = None, subtype: str = None, data: str = "", user: UserBase = None, device: DeviceBase = None, artifacts: list = [], source: str = "", hash: str = "", service: str = "") -> None:
        self.time:datetime = time
        self.type:str = type
        self.subtype:str = subtype
        self.data:str = data
        self.user:UserBase = user
        self.device:DeviceBase = device
        self.artifacts:list = artifacts
        self.source:str = source
        self.hash:str = hash
        self.service:str = service


    def __eq__(self, __o: object) -> bool:
        return self.type == __o.type and self.subtype == __o.subtype and self.time == __o.time


    def print(self) -> None:
        user_name = self.user.name if self.user else ''
        print(f"{self.time.strftime('%Y-%m-%d %H:%M:%S')} [{self.type:10}] {self.subtype:25} {self.data[0:45]:45} {user_name:15} {self.device.id if self.device else ''}")
