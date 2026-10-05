"""
UCO/CASE namespaces. Generated individuals sit in the same ontology (same base IRI, same imports).
"""
from rdflib import Namespace

CASE_IRI = "https://ontology.caseontology.org/case/case"
CASE = Namespace(CASE_IRI + "#")
CORE = Namespace("https://ontology.unifiedcyberontology.org/uco/core/")
TYPES = Namespace("https://ontology.unifiedcyberontology.org/uco/types/")
IDENTITY = Namespace("https://ontology.unifiedcyberontology.org/uco/identity/")
OBSERVABLE = Namespace("https://ontology.unifiedcyberontology.org/uco/observable/")
VOCABULARY = Namespace("https://ontology.unifiedcyberontology.org/uco/vocabulary/")

# Pinned to the exact release this generator targets.Bump ONTOLOGY_VERSION 
# and re-verify against src/reference_ontologies/ when moving to a newer release.
ONTOLOGY_VERSION = "1.5.0"
CASE_INVESTIGATION_IRI = f"https://ontology.caseontology.org/case/investigation/{ONTOLOGY_VERSION}"
CASE_VOCABULARY_IRI = f"https://ontology.caseontology.org/case/vocabulary/{ONTOLOGY_VERSION}"
UCO_IRI = f"https://ontology.unifiedcyberontology.org/uco/uco/{ONTOLOGY_VERSION}"


_UNSAFE_CHARS = {
    " ": "_",
    "(": "",
    ")": "",
    "@": "_at_",   # e.g. an email used as a name/id -> IRI fragment
    "/": "-",
    "\\": "-",
    "#": "",
    "%": "",
    '"': "",
    "'": "",
}


def sanitize(value: str) -> str:
    """Turn an arbitrary extracted string (a name, a device id, a filename,
    an email address used as one of those) into a safe IRI local name.
    Escape anything that isn't safe as a Manchester-syntax / QName-style 
    local name."""
    result = str(value)
    for char, replacement in _UNSAFE_CHARS.items():
        result = result.replace(char, replacement)
    return result


def camel(kind: str) -> str:
    """'originates-from-device' -> 'originatesFromDevice', matching the
    relationship naming convention used in the old system."""
    words = kind.split("-")
    return words[0] + "".join(w.capitalize() for w in words[1:])
