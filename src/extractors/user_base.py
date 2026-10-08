class UserBase:
    def __init__(self, type: str, name: str, events: list = [], artifacts: list = [], devices: list = [], source: str = "", hash: str = "", associates: list = [], notes: str = "") -> None:
        self.type:str = type
        self.name:str = name
        self.events:list = events
        self.artifacts:list = artifacts
        self.devices:list = devices
        self.source:str = source
        self.hash:str = hash
        self.associates:list = associates  # Known-facts-only field (KnownFactsExtractor)
        self.notes:str = notes  # Known-facts-only field (KnownFactsExtractor)


    def __eq__(self, __o: object) -> bool:
        return self.type == __o.type and self.name == __o.name


    def print(self) -> None:
        print(f"{self.type:15} {self.name}")
