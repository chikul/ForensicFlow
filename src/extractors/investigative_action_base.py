class InvestigativeActionBase:
    """A known-facts-only record (KnownFactsExtractor): one step of the
    chain-of-custody/acquisition narrative from known_facts.yaml's
    investigative_actions, carrying just enough to populate
    investigation:InvestigativeAction (performer, object, location,
    wasInformedBy).

    Not part of the UserBase/DeviceBase/EventBase/ArtifactBase quad every
    carve() returns: InvestigativeAction's own properties (and the role
    assignment that names its performer) don't fit that shape, so
    KnownFactsExtractor hands these back separately, via
    carve_investigation() rather than carve().
    """
    def __init__(self, id: str, label: str, performer: str = "", objects: list = None,
                 location: str = "", was_informed_by: list = None, source: str = "", hash: str = "") -> None:
        self.id: str = id
        self.label: str = label
        self.performer: str = performer
        # list of (device_type, device_id) tuples, matching DeviceBase keys
        self.objects: list = objects if objects is not None else []
        self.location: str = location
        # list of other InvestigativeActionBase.id values this action
        # wasInformedBy
        self.was_informed_by: list = was_informed_by if was_informed_by is not None else []
        self.source: str = source
        self.hash: str = hash
