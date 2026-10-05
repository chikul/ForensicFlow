"""
Validates a CASE/UCO ontology file three ways:

1. RDF/XML well-formedness (rdflib parse).
2. Every rdf:type and every predicate used in the file actually exists in
   the real UCO/CASE vocabularies, checked against the authoritative .ttl 
   sources fetched from the casework/CASE and ucoProject/UCO GitHub repos 
   into src/reference_ontologies/.
3. Every IRI local name is safe to type/edit inside Protege's
   Manchester-syntax widgets (helped to catch the '@'-in-email bug:
   the file parses and loads fine, but Protege's name-entry fields choke
   on characters like '@' that are legal in an IRI but not in a bare
   QName-style local name, showing "Invalid individual name" the moment
   you try to interact with that individual by hand).

Usage:
    python3 src/validate_ontology.py output/case_generated.owl
    python3 src/validate_ontology.py <any other .owl file>
"""
import re
import sys
from pathlib import Path

from rdflib import Graph, OWL, RDF, RDFS, URIRef

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = Path(__file__).resolve().parent / "reference_ontologies"

# Characters that are legal in an IRI but that break Protege's bare
# Manchester-syntax name entry (rename/new-individual/type-to-add fields).
UNSAFE_LOCAL_NAME_CHARS = re.compile(r"[@%\"'\\\s]")

_CLASS_TYPES = {OWL.Class, RDFS.Class}
_PROPERTY_TYPES = {OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty}
_IGNORED_TYPES = {OWL.NamedIndividual, OWL.Ontology, OWL.Class, OWL.ObjectProperty,
                   OWL.DatatypeProperty, OWL.AnnotationProperty, RDF.Property}


def load_reference_vocabulary() -> Graph:
    g = Graph()
    ttl_files = sorted(REFERENCE_DIR.glob("*.ttl"))
    if not ttl_files:
        raise SystemExit(
            f"No reference ontology .ttl files found in {REFERENCE_DIR}. "
            "Fetch uco_core.ttl, uco_observable.ttl, uco_identity.ttl, "
            "uco_types.ttl, uco_vocabulary.ttl, case_case.ttl, "
            "case_investigation.ttl, case_vocabulary.ttl there first."
        )
    for f in ttl_files:
        g.parse(str(f), format="turtle")
    return g


def known_classes_and_properties(vocab: Graph):
    classes = {s for s, _, o in vocab.triples((None, RDF.type, None)) if o in _CLASS_TYPES}
    properties = {s for s, _, o in vocab.triples((None, RDF.type, None)) if o in _PROPERTY_TYPES}
    return classes, properties


def check_well_formed(path: Path):
    g = Graph()
    try:
        g.parse(str(path), format="xml")
    except Exception as exc:  # noqa: BLE001
        return None, [f"FILE DOES NOT PARSE AS RDF/XML: {exc}"]
    return g, []


def check_vocabulary_usage(g: Graph, known_classes, known_properties):
    problems = []
    used_types = {o for _, _, o in g.triples((None, RDF.type, None))}
    unknown_types = {t for t in used_types if t not in _IGNORED_TYPES and t not in known_classes}
    for t in sorted(unknown_types):
        problems.append(f"UNKNOWN CLASS used as rdf:type, not found in UCO/CASE: <{t}>")

    used_predicates = {p for _, p, _ in g if p != RDF.type}
    unknown_predicates = {p for p in used_predicates if p not in known_properties and str(p).startswith(
        ("https://ontology.unifiedcyberontology.org/", "https://ontology.caseontology.org/")
    )}
    for p in sorted(unknown_predicates):
        problems.append(f"UNKNOWN PROPERTY used, not found in UCO/CASE: <{p}>")
    return problems


def check_local_name_safety(g: Graph):
    problems = []
    seen = set()
    for term in set(g.subjects()) | {o for o in g.objects() if isinstance(o, URIRef)}:
        if not isinstance(term, URIRef):
            continue
        if "#" not in str(term):
            continue
        frag = str(term).rsplit("#", 1)[-1]
        if frag in seen:
            continue
        seen.add(frag)
        if UNSAFE_LOCAL_NAME_CHARS.search(frag):
            problems.append(
                f"UNSAFE LOCAL NAME (breaks Protege's name-entry widgets): '{frag}'"
            )
    return problems


def validate(path: Path, vocab: Graph, known_classes, known_properties):
    print(f"\n=== Validating {path} ===")
    g, problems = check_well_formed(path)
    if g is None:
        for p in problems:
            print(" -", p)
        return False

    print(f"Parsed OK: {len(g)} triples, {len(set(g.subjects()))} distinct subjects")

    problems = []
    problems += check_vocabulary_usage(g, known_classes, known_properties)
    problems += check_local_name_safety(g)

    if not problems:
        print("No problems found.")
        return True

    print(f"{len(problems)} problem(s):")
    for p in problems:
        print(" -", p)
    return False


def main():
    targets = [Path(p) for p in sys.argv[1:]] or [
        REPO_ROOT / "output" / "case_generated.owl",
    ]

    print("Loading reference UCO/CASE vocabulary...")
    vocab = load_reference_vocabulary()
    known_classes, known_properties = known_classes_and_properties(vocab)
    print(f"Reference vocabulary: {len(known_classes)} classes, {len(known_properties)} properties")

    ok = True
    for target in targets:
        ok = validate(target, vocab, known_classes, known_properties) and ok

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
