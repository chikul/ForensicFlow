"""
CaseGraphBuilder turns the plain-Python evidence objects the
extractors produce (UserBase, DeviceBase, EventBase, ArtifactBase)
into a UCO/CASE-compliant rdflib.Graph.

Scope (baseline pass, see conversation): map what the extractors already
parse into correct UCO/CASE classes and uco-observable:ObservableRelationship
links, plus observable:ApplicationAccount individuals and an "ownedBy"
ObservableRelationship (account -> identity:Person) carrying a
core:ConfidenceFacet, fed by Myers-diff string similarity (see
add_ownership() below and myers_diff.py) rather than exact-match entity
merging (see run_case_export.merge_duplicate_records() for that separate,
earlier pass).

Pinned to UCO/CASE 1.5.0 (see namespaces.ONTOLOGY_VERSION).
"""
import os

import rdflib
# Keep exact lexical forms for typed literals (e.g. "...T10:22:30Z" instead
# of rdflib silently round-tripping xsd:dateTime through Python's datetime
# and re-serializing UTC as "+00:00"). Must be set before any Literal(...,
# datatype=...) is constructed.
rdflib.NORMALIZE_LITERALS = False

from rdflib import Graph, Literal, RDF, URIRef, XSD  # noqa: E402
from rdflib.namespace import OWL  # noqa: E402

from .file_evidence import file_stats
from .namespaces import (
    CASE,
    CASE_INVESTIGATION_IRI,
    CASE_IRI,
    CASE_VOCABULARY_IRI,
    CORE,
    IDENTITY,
    OBSERVABLE,
    ONTOLOGY_VERSION,
    TYPES,
    UCO_IRI,
    VOCABULARY,
    camel,
    sanitize,
)

# device_type (as produced by the extractors) -> CASE Application
# individual, matching the three Application/ApplicationFacet pairs.
APPLICATION_BY_DEVICE_TYPE = {
    "Amazon": ("Amazon_Alexa", "Amazon Alexa", "1.1.0"),
    "NEST": ("NEST_Protect", "Nest Protect", "2.1.0"),
    "iSmartAlarm": ("iSmartAlarm", "iSmart Alarm", "1.0.0"),
}

# Local-name prefixes stripped off when building a relationship's own
# fragment, so e.g. "device:Amazon_Echo" contributes "Amazon_Echo" and
# "eventrecord-2018...:AmazonEcho:History" contributes
# "2018...:AmazonEcho:History"
_STRIPPABLE_PREFIXES = (
    "eventrecord-",
    "device:",
    "person:",
    "application:",
    "applicationaccount:",
    "file:",
    "emailaddress:",
    "digitaladdress:",
    "ipv4address:",
)


def _xml_escape_text(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _xml_escape_attr(value: str) -> str:
    return _xml_escape_text(value).replace('"', "&quot;")


def _local_name(term: URIRef) -> str:
    frag = str(term).rsplit("#", 1)[-1]
    for prefix in _STRIPPABLE_PREFIXES:
        if frag.startswith(prefix):
            return frag[len(prefix):]
    return frag


class CaseGraphBuilder:
    def __init__(self):
        self.g = Graph()
        self.g.bind("case", CASE)
        self.g.bind("core", CORE)
        self.g.bind("types", TYPES)
        self.g.bind("identity", IDENTITY)
        self.g.bind("observable", OBSERVABLE)
        self.g.bind("vocabulary", VOCABULARY)
        self.g.bind("owl", OWL)

        self._persons = {}
        self._applications = {}
        self._devices = {}
        self._events = {}
        self._artifacts = {}
        self._application_accounts = {}
        self._files = {}
        self._ip_addresses = {}
        self._relationships = {}

        self._add_ontology_header()

    def _add_ontology_header(self):
        onto = URIRef(CASE_IRI)
        self.g.add((onto, RDF.type, OWL.Ontology))
        self.g.add((onto, OWL.imports, URIRef(CASE_INVESTIGATION_IRI)))
        self.g.add((onto, OWL.imports, URIRef(CASE_VOCABULARY_IRI)))
        self.g.add((onto, OWL.imports, URIRef(UCO_IRI)))
        self.g.add((onto, OWL.versionInfo, Literal(ONTOLOGY_VERSION)))

    def _declare(self, uri: URIRef, class_iri) -> None:
        """Every individual the original hand-built ontology declared was
        wrapped in owl:NamedIndividual *and* typed with its domain class --
        mirror both triples here so Protege's Individuals view and any OWL
        DL reasoner treat these exactly the same way."""
        self.g.add((uri, RDF.type, OWL.NamedIndividual))
        self.g.add((uri, RDF.type, class_iri))

    # ------------------------------------------------------------------
    # identity:Person
    # ------------------------------------------------------------------
    def add_person(self, name: str) -> URIRef:
        if name in self._persons:
            return self._persons[name]

        local = sanitize(name)
        uri = CASE[f"person:{local}"]
        facet = CASE[f"simplenamefacet:{local}"]

        parts = name.split(" ")
        given = " ".join(parts[:-1]) if len(parts) > 1 else name
        family = parts[-1] if len(parts) > 1 else None

        self._declare(uri, IDENTITY.Person)
        self.g.add((uri, CORE.hasFacet, facet))

        self._declare(facet, IDENTITY.SimpleNameFacet)
        self.g.add((facet, IDENTITY.givenName, Literal(given, datatype=XSD.string)))
        if family:
            self.g.add((facet, IDENTITY.familyName, Literal(family, datatype=XSD.string)))

        self._persons[name] = uri
        return uri

    # ------------------------------------------------------------------
    # observable:Application (+ ApplicationFacet)
    # ------------------------------------------------------------------
    def add_application(self, device_type: str):
        info = APPLICATION_BY_DEVICE_TYPE.get(device_type)
        if info is None:
            return None

        key, label, version = info
        if key in self._applications:
            return self._applications[key]

        uri = CASE[f"application:{key}"]
        facet = CASE[f"applicationfacet:{key}"]

        self._declare(uri, OBSERVABLE.Application)
        self.g.add((uri, CORE.hasFacet, facet))

        self._declare(facet, OBSERVABLE.ApplicationFacet)
        self.g.add((facet, OBSERVABLE.applicationIdentifier, Literal(label, datatype=XSD.string)))
        self.g.add((facet, OBSERVABLE.version, Literal(version, datatype=XSD.string)))

        self._applications[key] = uri
        return uri

    # ------------------------------------------------------------------
    # observable:ApplicationAccount (+ AccountFacet, ApplicationAccountFacet)
    # ------------------------------------------------------------------
    def add_application_account(self, device_type: str, account_identifier: str):
        """An account a suspect holds within one of the Applications above
        (Amazon's customer_id, iSmartAlarm's operator username, NEST's
        login email).
        """
        application_uri = self.add_application(device_type)

        key = (device_type, account_identifier)
        if key in self._application_accounts:
            return self._application_accounts[key]

        local = sanitize(f"{device_type} {account_identifier}")
        uri = CASE[f"applicationaccount:{local}"]
        account_facet = CASE[f"accountfacet:{local}"]
        app_account_facet = CASE[f"applicationaccountfacet:{local}"]

        self._declare(uri, OBSERVABLE.ApplicationAccount)
        self.g.add((uri, CORE.hasFacet, account_facet))
        self.g.add((uri, CORE.hasFacet, app_account_facet))

        self._declare(account_facet, OBSERVABLE.AccountFacet)
        self.g.add((account_facet, OBSERVABLE.accountIdentifier, Literal(account_identifier, datatype=XSD.string)))

        self._declare(app_account_facet, OBSERVABLE.ApplicationAccountFacet)
        if application_uri is not None:
            self.g.add((app_account_facet, OBSERVABLE.application, application_uri))

        self._application_accounts[key] = uri
        return uri

    def application_accounts(self):
        """Read-only view of every (device_type, account_identifier) ->
        ApplicationAccount URI created so far, for the entity-resolution
        postprocessing step to iterate over."""
        return dict(self._application_accounts)

    # ------------------------------------------------------------------
    # "ownedBy": ApplicationAccount -> identity:Person, with a
    # core:ConfidenceFacet (entity resolution via Myers-diff string
    # similarity - see myers_diff.py and run_case_export.py)
    # ------------------------------------------------------------------
    def add_ownership(self, account_uri: URIRef, person_uri: URIRef, confidence_percent: int) -> URIRef:
        """Same ObservableRelationship mechanism as every other link in
        this graph, carrying a core:ConfidenceFacet, since this link is
        asserted by string-similarity matching rather than being directly 
        observed in the source data.

        Note: ApplicationAccount is an observable:Observable, but
        identity:Person is not, so this ObservableRelationship's target
        doesn't satisfy the SHACL shape's advisory that both source and
        target of an ObservableRelationship be Observables. That shape
        constraint is sh:Warning severity in 1.5.0 (explicitly slated to
        become an error only in UCO 2.0.0) and is already true of every
        Person-linking relationship this generator builds!
        """
        if not (0 <= confidence_percent <= 100):
            raise ValueError(f"confidence_percent must be 0-100, got {confidence_percent}")

        relationship_uri = self.add_relationship(account_uri, person_uri, "ownedBy")

        local = f"{_local_name(account_uri)}-{_local_name(person_uri)}"
        facet = CASE[f"confidencefacet:{local}"]

        self.g.add((relationship_uri, CORE.hasFacet, facet))
        self._declare(facet, CORE.ConfidenceFacet)
        self.g.add((facet, CORE.confidence, Literal(confidence_percent, datatype=XSD.nonNegativeInteger)))

        return relationship_uri

    # ------------------------------------------------------------------
    # observable:Device (+ DeviceFacet)
    # ------------------------------------------------------------------
    def add_device(self, device_type: str, device_id: str, hardware_id: str = "", observed_ip: str = "") -> URIRef:
        key = (device_type, device_id)
        if key in self._devices:
            return self._devices[key]

        local = sanitize(f"{device_type} {device_id}")
        uri = CASE[f"device:{local}"]
        facet = CASE[f"devicefacet:{local}"]

        # observable:SmartDevice, not the generic observable:Device: every
        # device this project extracts (Amazon Echo, NEST Protect, the
        # iSmartAlarm hub and its sensors)
        self._declare(uri, OBSERVABLE.SmartDevice)
        self.g.add((uri, CORE.hasFacet, facet))

        self._declare(facet, OBSERVABLE.DeviceFacet)
        self.g.add((facet, OBSERVABLE.deviceType, Literal(f"{device_type} {device_id}", datatype=XSD.string)))
        # DeviceFacet's own observable:serialNumber for the device's real
        # hardware/serial identifier, as distinct from device_id above
        if hardware_id:
            self.g.add((facet, OBSERVABLE.serialNumber, Literal(hardware_id, datatype=XSD.string)))

        self._devices[key] = uri

        # observed_ip is a static, undated config-history fact about the
        # device, not something tied to any specific dated event, so it's 
        # modeled as a plain ObservableRelationship to a standalone 
        # IPv4Address
        if observed_ip:
            ip_uri = self.add_ip_address(observed_ip)
            self.add_relationship(uri, ip_uri, "associated-with-ip-address")

        return uri

    # ------------------------------------------------------------------
    # observable:IPv4Address (+ IPv4AddressFacet)
    # ------------------------------------------------------------------
    def add_ip_address(self, ip: str) -> URIRef:
        if ip in self._ip_addresses:
            return self._ip_addresses[ip]

        local = sanitize(ip)
        uri = CASE[f"ipv4address:{local}"]
        facet = CASE[f"ipv4addressfacet:{local}"]

        self._declare(uri, OBSERVABLE.IPv4Address)
        self.g.add((uri, CORE.hasFacet, facet))

        # IPv4AddressFacet -> IPAddressFacet -> DigitalAddressFacet, whose
        # own observable:addressValue is exactly the property already used
        # for EmailAddress/DigitalAddress above
        self._declare(facet, OBSERVABLE.IPv4AddressFacet)
        self.g.add((facet, OBSERVABLE.addressValue, Literal(ip, datatype=XSD.string)))

        self._ip_addresses[ip] = uri
        return uri

    # ------------------------------------------------------------------
    # observable:EventRecord (+ EventRecordFacet)
    # ------------------------------------------------------------------
    def add_event(self, event, application_uri=None, device_uri=None) -> URIRef:
        key = (event.time, event.type, event.subtype)
        if key in self._events:
            return self._events[key]

        time_str = event.time.strftime("%Y-%m-%dT%H:%M:%SZ")
        subtype_local = sanitize(event.subtype[0:20])
        frag = f"{time_str}:{event.type}:{subtype_local}"

        uri = CASE[f"eventrecord-{frag}"]
        facet = CASE[f"eventrecordfacet-{frag}"]

        self._declare(uri, OBSERVABLE.EventRecord)
        self.g.add((uri, CORE.hasFacet, facet))

        self._declare(facet, OBSERVABLE.EventRecordFacet)
        if application_uri is not None:
            self.g.add((facet, OBSERVABLE.application, application_uri))
        if device_uri is not None:
            self.g.add((facet, OBSERVABLE.eventRecordDevice, device_uri))
        if event.data:
            self.g.add((facet, OBSERVABLE.eventRecordText, Literal(event.data, datatype=XSD.string)))
        if getattr(event, "service", ""):
            self.g.add((facet, OBSERVABLE.eventRecordServiceName, Literal(event.service, datatype=XSD.string)))
        self.g.add((facet, OBSERVABLE.eventType, Literal(event.subtype, datatype=XSD.string)))
        self.g.add((facet, OBSERVABLE.observableCreatedTime, Literal(time_str, datatype=XSD.dateTime)))

        self._events[key] = uri
        return uri

    # ------------------------------------------------------------------
    # observable:EmailAddress / observable:DigitalAddress (+ facets)
    # ------------------------------------------------------------------
    def add_artifact(self, artifact):
        key = (artifact.type, artifact.id)
        if key in self._artifacts:
            return self._artifacts[key]

        if artifact.type == "Email":
            local = sanitize(artifact.id)
            uri = CASE[f"emailaddress:{local}"]
            facet = CASE[f"emailaddressfacet:{local}"]
            self._declare(uri, OBSERVABLE.EmailAddress)
            self.g.add((uri, CORE.hasFacet, facet))
            self._declare(facet, OBSERVABLE.EmailAddressFacet)
            self.g.add((facet, OBSERVABLE.addressValue, Literal(artifact.id, datatype=XSD.string)))
        else:
            local = sanitize(f"{artifact.type}:{artifact.id}")
            uri = CASE[f"digitaladdress:{local}"]
            facet = CASE[f"digitaladdressfacet:{local}"]
            self._declare(uri, OBSERVABLE.DigitalAddress)
            self.g.add((uri, CORE.hasFacet, facet))
            self._declare(facet, OBSERVABLE.DigitalAddressFacet)
            self.g.add((facet, OBSERVABLE.addressValue, Literal(artifact.id, datatype=XSD.string)))

        self._artifacts[key] = uri
        return uri

    # ------------------------------------------------------------------
    # observable:File / FileFacet / ContentDataFacet / types:Hash
    # ------------------------------------------------------------------
    def add_file_evidence(self, path: str, relative_path: str, precomputed_md5: str = None) -> URIRef:
        filename = os.path.basename(path)
        if filename in self._files:
            return self._files[filename]

        size, entropy, magic, md5_hex, sha256_hex = file_stats(path)
        if precomputed_md5:
            md5_hex = precomputed_md5

        local = sanitize(filename)
        uri = CASE[f"file:{local}"]
        filefacet = CASE[f"filefacet:{local}"]
        contentfacet = CASE[f"contentdatafacet:{local}"]
        md5_hash_uri = CASE[f"hash:{local}:MD5"]
        sha256_hash_uri = CASE[f"hash:{local}:SHA256"]

        extension = filename.rsplit(".", 1)[-1] if "." in filename else ""

        self._declare(uri, OBSERVABLE.File)
        self.g.add((uri, CORE.hasFacet, filefacet))
        self.g.add((uri, CORE.hasFacet, contentfacet))

        self._declare(filefacet, OBSERVABLE.FileFacet)
        self.g.add((filefacet, OBSERVABLE.extension, Literal(extension, datatype=XSD.string)))
        self.g.add((filefacet, OBSERVABLE.fileName, Literal(filename, datatype=XSD.string)))
        self.g.add((filefacet, OBSERVABLE.filePath, Literal(relative_path, datatype=XSD.string)))
        self.g.add((filefacet, OBSERVABLE.isDirectory, Literal(False, datatype=XSD.boolean)))
        self.g.add((filefacet, OBSERVABLE.sizeInBytes, Literal(size, datatype=XSD.integer)))

        self._declare(contentfacet, OBSERVABLE.ContentDataFacet)
        self.g.add((contentfacet, OBSERVABLE.hash, md5_hash_uri))
        self.g.add((contentfacet, OBSERVABLE.hash, sha256_hash_uri))
        self.g.add((contentfacet, OBSERVABLE.entropy, Literal(entropy, datatype=XSD.decimal)))
        self.g.add((contentfacet, OBSERVABLE.magicNumber, Literal(magic, datatype=XSD.string)))
        self.g.add((contentfacet, OBSERVABLE.sizeInBytes, Literal(size, datatype=XSD.integer)))

        self._declare(md5_hash_uri, TYPES.Hash)
        self.g.add((md5_hash_uri, TYPES.hashMethod, Literal("MD5", datatype=XSD.string)))
        self.g.add((md5_hash_uri, TYPES.hashValue, Literal(md5_hex, datatype=XSD.hexBinary)))

        self._declare(sha256_hash_uri, TYPES.Hash)
        self.g.add((sha256_hash_uri, TYPES.hashMethod, Literal("SHA256", datatype=XSD.string)))
        self.g.add((sha256_hash_uri, TYPES.hashValue, Literal(sha256_hex, datatype=XSD.hexBinary)))

        self._files[filename] = uri
        return uri

    # ------------------------------------------------------------------
    # observable:ObservableRelationship
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # core:description - a free-text annotation usable on any
    # core:UcoObject (persons, devices, ...). Used for investigator notes
    # carried in known_facts.yaml (e.g. "claims reported by associates,
    # not independently verified") that don't fit any other facet.
    # ------------------------------------------------------------------
    def add_description(self, uri: URIRef, text: str) -> None:
        if not text:
            return
        self.g.add((uri, CORE.description, Literal(text, datatype=XSD.string)))

    def add_relationship(self, source_uri: URIRef, target_uri: URIRef, kind: str, directional: bool = True):
        key = (source_uri, target_uri, kind)
        if key in self._relationships:
            return self._relationships[key]

        rel_local = f"{camel(kind)}-{_local_name(source_uri)}-{_local_name(target_uri)}"
        uri = CASE[f"relationship:{rel_local}"]

        self._declare(uri, OBSERVABLE.ObservableRelationship)
        self.g.add((uri, CORE.source, source_uri))
        self.g.add((uri, CORE.target, target_uri))
        self.g.add((uri, CORE.isDirectional, Literal(directional, datatype=XSD.boolean)))
        self.g.add((uri, CORE.kindOfRelationship, Literal(kind, datatype=XSD.string)))

        self._relationships[key] = uri
        return uri

    # ------------------------------------------------------------------
    def serialize(self, path: str):
        """Hand-rolled RDF/XML writer instead of self.g.serialize(format="xml").

        rdflib's own serializer iterates Python sets/dicts internally, whose
        order depends on CPython's per-process string hash randomization
        (PYTHONHASHSEED). Two runs over the identical graph therefore
        produce byte-different files (same triples, different line order, 
        which shows up as a full-file rewrite in git even when nothing
        semantically changed. This writer sorts everything (namespaces,
        subjects, and each subject's properties) so the same graph always
        serializes to the same bytes, and only real content changes show
        up in a diff. Duhh..
        """
        lines = ["<?xml version=\"1.0\" encoding=\"utf-8\"?>", "<rdf:RDF"]
        for prefix, ns_uri in sorted(self.g.namespaces(), key=lambda pn: pn[0]):
            if not prefix:
                continue
            lines.append(f'  xmlns:{prefix}="{_xml_escape_attr(str(ns_uri))}"')
        lines[-1] += ">"

        by_subject = {}
        for s, p, o in self.g:
            by_subject.setdefault(s, []).append((p, o))

        def prop_sort_key(item):
            p, o = item
            if p == RDF.type:
                rank = 0 if o == OWL.NamedIndividual else 1
            else:
                rank = 2
            return (rank, str(p), str(o))

        for subject in sorted(by_subject, key=str):
            lines.append(f'  <rdf:Description rdf:about="{_xml_escape_attr(str(subject))}">')
            for predicate, obj in sorted(by_subject[subject], key=prop_sort_key):
                tag = self.g.namespace_manager.qname(predicate)
                if isinstance(obj, URIRef):
                    lines.append(f'    <{tag} rdf:resource="{_xml_escape_attr(str(obj))}"/>')
                else:
                    text = _xml_escape_text(str(obj))
                    if obj.datatype:
                        lines.append(
                            f'    <{tag} rdf:datatype="{_xml_escape_attr(str(obj.datatype))}">{text}</{tag}>'
                        )
                    elif obj.language:
                        lines.append(f'    <{tag} xml:lang="{obj.language}">{text}</{tag}>')
                    else:
                        lines.append(f"    <{tag}>{text}</{tag}>")
            lines.append("  </rdf:Description>")
        lines.append("</rdf:RDF>")
        lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def stats(self):
        return {
            "persons": len(self._persons),
            "applications": len(self._applications),
            "application_accounts": len(self._application_accounts),
            "devices": len(self._devices),
            "events": len(self._events),
            "artifacts": len(self._artifacts),
            "files": len(self._files),
            "ip_addresses": len(self._ip_addresses),
            "relationships": len(self._relationships),
        }
