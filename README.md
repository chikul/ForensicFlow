# ForensicFlow

A UCO/CASE-compliant digital-forensics ontology built from the DFRWS 2018
IoT dataset (Amazon Echo, NEST Protect, iSmartAlarm). Companion code for
the 2021 and 2024 papers in `papers/`; see `CHANGELOG.md` for the
project's history.

Ontology generation: `src/run_case_export.py` runs the extractors in
`src/extractors/` against the raw evidence in `data/` and writes a fresh,
UCO/CASE 1.5.0-compliant `output/case_generated.owl` plus a human-readable
`output/timeline.csv`.

## Layout

```text
data/                     Raw evidence (Alexa SQLite DB, iSmartAlarm
                           SQLite DB, NEST JSON cache) - extractor input.
src/
  extractors/              Per-source parsing (Alexa/iSmartAlarm/NEST
                            carve() implementations) and the shared
                            UserBase/DeviceBase/EventBase/ArtifactBase
                            record types they return.
  case_ontology/            Turns those records into a UCO/CASE 1.5.0
                            rdflib.Graph: individuals, facets,
                            ObservableRelationships, entity merging,
                            Myers-diff-based entity resolution
                            (myers_diff.py), and a deterministic RDF/XML
                            writer.
  reference_ontologies/     UCO/CASE 1.5.0 .ttl sources (pinned, fetched
                            from the ucoProject/UCO and casework/CASE
                            repos), used by validate_ontology.py as the
                            ground truth for "is this term real".
  run_case_export.py        Orchestrates the whole export - entry point.
  validate_ontology.py      Checks an .owl file for well-formedness,
                            unknown vocabulary terms, and IRI-safety
                            issues (the kind of thing that shows up as
                            "Invalid individual name" in Protege).
output/                   Generated artifacts: case_generated.owl and
                           timeline.csv.
papers/                   The 2021 and 2024 papers this project accompanies.
```

## Running the export

```bash
python3 src/run_case_export.py
```

Requires `rdflib`. Regenerates `output/case_generated.owl` and
`output/timeline.csv` from the raw data in `data/`, printing extraction,
entity-merge, and entity-resolution (ownedBy) stats as it goes.

## Validating an ontology file

```bash
python3 src/validate_ontology.py                              # output/case_generated.owl
python3 src/validate_ontology.py output/case_generated.owl     # equivalent, explicit
```

`validate_ontology.py` checks well-formedness, unknown vocabulary terms,
and IRI safety, but not full SHACL shape conformance (cardinality,
datatype, and controlled-vocabulary constraints). For that, run `pyshacl`
directly (`pip install pyshacl`) with `src/reference_ontologies/*.ttl` as
both the shapes graph and the ontology graph (for OWL-subclass reasoning):

```python
import pyshacl, glob
from rdflib import Graph

data = Graph().parse("output/case_generated.owl", format="xml")
shapes = Graph(); ont = Graph()
for f in glob.glob("src/reference_ontologies/*.ttl"):
    shapes.parse(f, format="turtle")
    ont.parse(f, format="turtle")

conforms, _, report = pyshacl.validate(
    data, shacl_graph=shapes, ont_graph=ont, inference="rdfs", advanced=True
)
print(report)
```

As of the last full run: 0 `sh:Violation`-severity results. The remaining
lower-severity results are documented, accepted characteristics of this
generator (human-readable IRIs instead of UUID suffixes; Person as an
ObservableRelationship source/target, which only becomes an error in a
hypothetical UCO 2.0.0) rather than open bugs.
