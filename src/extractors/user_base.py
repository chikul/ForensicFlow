class UserBase:
    def __init__(self, type: str, name: str, events: list = [], artifacts: list = [], devices: list = [], source: str = "", hash: str = "") -> None:
        self.type:str = type
        self.name:str = name
        self.events:list = events
        self.artifacts:list = artifacts
        self.devices:list = devices
        self.source:str = source
        self.hash:str = hash


    def __eq__(self, __o: object) -> bool:
        return self.type == __o.type and self.name == __o.name


    def print(self) -> None:
        print(f"{self.type:15} {self.name}")
