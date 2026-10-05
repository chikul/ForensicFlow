import hashlib

class ArtifactBase:
    def __init__(self, type: str, id: str, data: str = "", events: list = [], devices: list = [], users: list = [], source: str = "", hash: str = "") -> None:
        self.type: str = type
        self.id: str = id
        self.data: str = data
        self.events:list = events
        self.devices:list = devices
        self.users:list = users
        self.source:str = source
        self.hash:str = hash


    def __eq__(self, __o: object) -> bool:
        return self.type == __o.type and self.id == __o.id


    def __hash__(self) -> int:
        return int(hashlib.sha1(f"{self.type}.{self.id}.{self.data}".encode("utf-8")).hexdigest(), 16)


    def print(self) -> None:
        print(f"{self.type:15} {self.id} {self.data}")
