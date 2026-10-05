class DeviceBase:
    def __init__(self, type: str, id: str, events: list = [], artifacts: list = [], users: list = [], source: str = "", hash: str = "", hardware_id: str = "", observed_ip: str = "") -> None:
        self.type:str = type
        self.id:str = id
        self.events:list = events
        self.artifacts:list = artifacts
        self.users:list = users
        self.source:str = source
        self.hash:str = hash
        self.hardware_id:str = hardware_id
        self.observed_ip:str = observed_ip


    def __eq__(self, __o: object) -> bool:
        return self.type == __o.type and self.id == __o.id


    def print(self) -> None:
        print(f"{self.type:15} {self.id}")
