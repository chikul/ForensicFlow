"""
Generates output/case_generated.owl: a UCO/CASE-compliant ontology
population built by running the extractors.

Every UserBase/DeviceBase/EventBase/ArtifactBase produced is handed to
CaseGraphBuilder, which knows how to express the facts as UCO/CASE
individuals and uco-observable:ObservableRelationship links.

Run from anywhere:
    python3 src/run_case_export.py
"""
import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from extractors import (  # noqa: E402
    AlexaRdfExport,
    IsaRdfExport,
    KnownFactsExtractor,
    NestRdfExport,
)
from case_ontology import CaseGraphBuilder, similarity_ratio  # noqa: E402

DATA_DIR = REPO_ROOT / "data"
ALEXA_DATABASE_PATH = DATA_DIR / "(2018-07-01_13.17.01)_CIFT_RESULT" / "cift_amazon_alexa.db"
ISA_DATABASE_PATH = DATA_DIR / "iSA.common" / "databases" / "iSmartAlarm.DB"
NEST_CACHE_PATH = DATA_DIR / "com.nest.android" / "cache" / "cache" / "cache-1332523362.json"
KNOWN_FACTS_PATH = DATA_DIR / "known_facts.yaml"

TZ_DELTA = 7200
TZ_INFO = timezone(timedelta(seconds=TZ_DELTA))
TIMEFRAME_START = datetime(2018, 5, 17, 0, 0, tzinfo=TZ_INFO)
TIMEFRAME_END = datetime(2018, 5, 17, 23, 59, tzinfo=TZ_INFO)

OUTPUT_PATH = REPO_ROOT / "output" / "case_generated.owl"
TIMELINE_CSV_PATH = REPO_ROOT / "output" / "timeline.csv"

# Entity resolution threshold: minimum Myers-diff similarity_ratio() an
# ApplicationAccount identifier must reach against a known suspect's real
# name before an "ownedBy" edge is asserted. Chosen empirically against
# this dataset's five accounts: "JPinkman" (0.727) and "pandadodu" (0.526)
# clearly resemble their real suspects and clear this bar; "TheBoss"
# (0.286), Amazon's opaque customer id "A2F07N8TDIAK5U" (0.333), and
# NEST's login email "jpinkman2018@gmail.com" (0.444, a coincidental
# partial character overlap, not a real name resemblance) all correctly
# stay unresolved below it.
OWNERSHIP_CONFIDENCE_THRESHOLD = 0.5

ACCOUNT_HANDLE_USER_TYPES = {"iSmartAlarm", "NEST"}


def relative_path(abs_path: Path) -> str:
    return "./data/" + os.path.relpath(str(abs_path), start=str(DATA_DIR)).replace(os.sep, "/")


def write_timeline_csv(events, path: Path) -> None:
    """Table-1-style consolidated timeline export (paper Sec. 3.5): one row
    per event, in chronological order, human-readable rather than RDF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Time", "Type", "Subtype", "Description", "Service",
            "User", "Device Type", "Device ID",
            "Source", "Source Hash",
        ])
        for event in events:
            writer.writerow([
                event.time.isoformat() if event.time else "",
                event.type or "",
                event.subtype or "",
                event.data or "",
                getattr(event, "service", "") or "",
                event.user.name if event.user else "",
                event.device.type if event.device else "",
                event.device.id if event.device else "",
                relative_path(Path(event.source)) if event.source else "",
                event.hash or "",
            ])


def merge_duplicate_records(records, list_attrs=("events", "artifacts", "devices", "users")):
    """Entity merging (paper Sec. 3.4), exact-match pass only.
    Returns how many merges were performed, for an audit trail."""
    merges = 0
    i = 0
    while i < len(records):
        j = i + 1
        while j < len(records):
            if records[i] == records[j]:
                for attr in list_attrs:
                    if hasattr(records[i], attr) and hasattr(records[j], attr):
                        getattr(records[i], attr).extend(getattr(records[j], attr))
                del records[j]
                merges += 1
            else:
                j += 1
        i += 1
    return merges


def main():
    users = []
    devices = []
    events = []
    artifacts = []

    # KnownFactsExtractor runs first and deliberately bypasses
    # TIMEFRAME_START/END - see known_facts.yaml and KnownFactsExtractor's
    # docstring. The other three carve real device telemetry and are
    # windowed to the scenario's timeframe as before.
    exporters = [
        ("Known facts", KnownFactsExtractor(str(KNOWN_FACTS_PATH)), KNOWN_FACTS_PATH),
        ("Alexa", AlexaRdfExport(str(ALEXA_DATABASE_PATH), time_frame_start=TIMEFRAME_START, time_frame_end=TIMEFRAME_END), ALEXA_DATABASE_PATH),
        ("iSmartAlarm", IsaRdfExport(str(ISA_DATABASE_PATH), time_frame_start=TIMEFRAME_START, time_frame_end=TIMEFRAME_END), ISA_DATABASE_PATH),
        ("NEST", NestRdfExport(str(NEST_CACHE_PATH), time_frame_start=TIMEFRAME_START, time_frame_end=TIMEFRAME_END), NEST_CACHE_PATH),
    ]

    builder = CaseGraphBuilder()

    suspect_users = []
    investigative_actions = []

    file_uris = {}
    for label, exporter, path in exporters:
        results = exporter.carve()
        users.extend(results[0])
        devices.extend(results[1])
        events.extend(results[2])
        artifacts.extend(results[3])

        if label == "Known facts":
            suspect_users.extend(results[0])
            examiner, investigative_actions = exporter.carve_investigation()
            if examiner is not None:
                users.append(examiner)

        file_uris[exporter.data_sorce] = builder.add_file_evidence(
            str(path), relative_path(path), precomputed_md5=exporter.source_hash
        )

        # Application accounts. Each exporter surfaces its account
        # identifier differently.
        account_device_type = results[0][0].type if results[0] else (results[1][0].type if results[1] else None)
        email_artifacts = [a for a in results[3] if a.type == "Email"]
        if account_device_type == "Amazon":
            # Amazon surfaces the account id (Amazon:id) and the login
            # email as two separate artifacts of the same person. Link
            # them with a "linkedEmail" ObservableRelationship.
            for artifact in results[3]:
                if artifact.type == "Amazon:id":
                    account_uri = builder.add_application_account("Amazon", artifact.id)
                    for email_artifact in email_artifacts:
                        email_uri = builder.add_artifact(email_artifact)
                        builder.add_relationship(account_uri, email_uri, "linkedEmail")
        elif account_device_type == "iSmartAlarm":
            # No email is ever captured for these accounts in this data
            # source - nothing to link.
            for user in results[0]:
                builder.add_application_account("iSmartAlarm", user.name)
        elif account_device_type == "NEST":
            # NEST logs in via email, so the account identifier and the
            # linked email's value happen to be the same string, still
            # modeled as two individuals (ApplicationAccount, EmailAddress)
            # joined by an explicit relationship same as Amazon.
            for artifact in email_artifacts:
                account_uri = builder.add_application_account("NEST", artifact.id)
                email_uri = builder.add_artifact(artifact)
                builder.add_relationship(account_uri, email_uri, "linkedEmail")

        print(f"{label:15} events extracted this run: {len(results[2])}")

    events.sort(key=lambda r: r.time)
    write_timeline_csv(events, TIMELINE_CSV_PATH)

    merge_counts = {
        "users": merge_duplicate_records(users),
        "devices": merge_duplicate_records(devices),
        "artifacts": merge_duplicate_records(artifacts),
    }

    # Devices only ever get created in the graph when an event points
    # to them (below). known_devices from known_facts.yaml have no
    # events of their own (no extractable telemetry - see
    # known_facts.yaml's comments), so they're registered explicitly
    # here; add_device() is cached by (type, id), so this is a no-op
    # for any device that an event below also references.
    for device in devices:
        device_uri = builder.add_device(
            device.type, device.id,
            hardware_id=getattr(device, "hardware_id", ""),
            observed_ip=getattr(device, "observed_ip", ""),
        )
        if getattr(device, "notes", ""):
            builder.add_description(device_uri, device.notes)
        if device.source in file_uris:
            builder.add_relationship(device_uri, file_uris[device.source], "extracted-from-file")

    for event in events:
        application_uri = builder.add_application(event.device.type) if event.device else None
        device_uri = builder.add_device(
            event.device.type, event.device.id,
            hardware_id=getattr(event.device, "hardware_id", ""),
            observed_ip=getattr(event.device, "observed_ip", ""),
        ) if event.device else None
        event_uri = builder.add_event(event, application_uri=application_uri, device_uri=device_uri)

        if device_uri is not None:
            builder.add_relationship(event_uri, device_uri, "originates-from-device")

        if event.user:
            if event.user.type in ACCOUNT_HANDLE_USER_TYPES:
                # The event is only ever tied to an account handle here,
                # not a verified real name.
                account_uri = builder.add_application_account(event.user.type, event.user.name)
                builder.add_relationship(event_uri, account_uri, "associated-with-account")
            else:
                person_uri = builder.add_person(event.user.name)
                builder.add_relationship(event_uri, person_uri, "associated-with-user")

        if event.source in file_uris:
            builder.add_relationship(event_uri, file_uris[event.source], "extracted-from-file")

    for user in users:
        if user.type in ACCOUNT_HANDLE_USER_TYPES:
            account_uri = builder.add_application_account(user.type, user.name)
            for artifact in user.artifacts:
                artifact_uri = builder.add_artifact(artifact)
                builder.add_relationship(account_uri, artifact_uri, "associated-with-artifact")
            if user.source in file_uris:
                builder.add_relationship(account_uri, file_uris[user.source], "extracted-from-file")
            continue

        person_uri = builder.add_person(user.name)
        for artifact in user.artifacts:
            artifact_uri = builder.add_artifact(artifact)
            builder.add_relationship(person_uri, artifact_uri, "associated-with-artifact")
        if getattr(user, "notes", ""):
            builder.add_description(person_uri, user.notes)
        if user.source in file_uris:
            builder.add_relationship(person_uri, file_uris[user.source], "extracted-from-file")

        # investigation:Subject / investigation:Examiner role assignment
        # (known_facts.yaml only - see UserBase.type for these two).
        if user.type == "Suspect":
            builder.add_subject_role(person_uri)
        elif user.type == "Examiner":
            builder.add_examiner_role(person_uri)

    # Known associates (known_facts.yaml "associates" pairs): a
    # non-directional "associated-with-person" link between two known
    # suspects, asserted by the investigation record rather than
    # observed in any device data.
    associate_count = 0
    seen_pairs = set()
    for user in users:
        if not getattr(user, "associates", []):
            continue
        person_uri = builder.add_person(user.name)
        for associate_name in user.associates:
            pair_key = frozenset((user.name, associate_name))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            associate_uri = builder.add_person(associate_name)
            builder.add_relationship(person_uri, associate_uri, "associated-with-person", directional=False)
            associate_count += 1

    # investigation:InvestigativeAction chain (known_facts.yaml's
    # investigative_actions - see KnownFactsExtractor.carve_investigation()).
    # Two passes: first create every action individual (so performer/object/
    # location are all resolved against things that already exist in the
    # graph), then wire wasInformedBy edges, which can reference an action
    # defined later in the same list.
    action_uris_by_id = {}
    known_device_uris = builder.devices()
    for action in investigative_actions:
        object_uris = []
        for device_key in action.objects:
            if device_key not in known_device_uris:
                raise ValueError(
                    f"known_facts.yaml: investigative action {action.id!r} references "
                    f"device {device_key!r}, which was never created in the graph"
                )
            object_uris.append(known_device_uris[device_key])

        performer_uri = builder.add_person(action.performer) if action.performer else None
        location_uri = builder.add_location(action.location) if action.location else None

        action_uri = builder.add_investigative_action(
            action.id, action.label,
            performer_uri=performer_uri, object_uris=object_uris, location_uri=location_uri,
        )
        action_uris_by_id[action.id] = action_uri

        if action.source in file_uris:
            builder.add_relationship(action_uri, file_uris[action.source], "extracted-from-file")

    for action in investigative_actions:
        for informing_id in action.was_informed_by:
            if informing_id not in action_uris_by_id:
                raise ValueError(
                    f"known_facts.yaml: investigative action {action.id!r} has "
                    f"was_informed_by {informing_id!r}, which doesn't match any action id"
                )
            builder.add_was_informed_by(action_uris_by_id[action.id], action_uris_by_id[informing_id])

    # Entity resolution (fuzzy pass): for every ApplicationAccount, find
    # the best-matching known suspect by Myers-diff character similarity
    # between the account's raw identifier and the suspect's real name,
    # and assert an "ownedBy" edge with a confidence score if it clears
    # OWNERSHIP_CONFIDENCE_THRESHOLD.
    ownership_count = 0
    for (device_type, account_identifier), account_uri in builder.application_accounts().items():
        best_suspect = None
        best_score = 0.0
        for suspect in suspect_users:
            score = similarity_ratio(account_identifier, suspect.name)
            if score > best_score:
                best_score = score
                best_suspect = suspect

        if best_suspect is not None and best_score >= OWNERSHIP_CONFIDENCE_THRESHOLD:
            confidence = round(best_score * 100)
            person_uri = builder.add_person(best_suspect.name)
            builder.add_ownership(account_uri, person_uri, confidence)
            ownership_count += 1
            print(f"  ownedBy: {device_type}:{account_identifier} -> {best_suspect.name} (confidence {confidence}, similarity {best_score:.3f})")
        else:
            print(f"  ownedBy: {device_type}:{account_identifier} -> no suspect matched (best similarity {best_score:.3f})")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    builder.serialize(str(OUTPUT_PATH))

    print("---------------------------------------------")
    print(f"Entity merges (exact-match only): {merge_counts}")
    print(f"Known associates (asserted, from known_facts.yaml): {associate_count}")
    print(f"Entity resolutions (fuzzy ownedBy): {ownership_count}")
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Wrote {TIMELINE_CSV_PATH}")
    print(f"Total events in timeline: {len(events)}")
    print(f"Graph builder stats: {builder.stats()}")


if __name__ == "__main__":
    main()
