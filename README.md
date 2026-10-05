# ForensicFlow

## An event-centric, UCO/CASE-compliant ontology framework for IoT digital forensics

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![UCO/CASE 1.5.0](https://img.shields.io/badge/UCO%2FCASE-1.5.0-informational.svg)](https://caseontology.org/)
[![MEDI 2021](https://img.shields.io/badge/MEDI%202021-10.1007%2F978--3--030--78428--7__6-blueviolet.svg)](https://doi.org/10.1007/978-3-030-78428-7_6)
[![ICISSP 2024](https://img.shields.io/badge/ICISSP%202024-10.5220%2F0012437700003648-blueviolet.svg)](https://doi.org/10.5220/0012437700003648)

**Pavel Chikul**
Department of Computer Systems, Tallinn University of Technology, Estonia
`pavel.tsikul@taltech.ee`

**Hayretdin Bahşi**
Northern Arizona University, United States
`Hayretdin.Bahsi@nau.edu`

**Olaf Maennel**
University of Adelaide, Australia
`olaf.maennel@adelaide.edu.au`

---

ForensicFlow is the companion codebase for two papers on ontology-based digital
forensics: an [initial ontology engineering case study (MEDI 2021)](https://doi.org/10.1007/978-3-030-78428-7_6)
and a full [event-centric semantic web framework (ICISSP 2024)](https://doi.org/10.5220/0012437700003648),
both building toward the same idea - correlating evidence from heterogeneous,
distributed sources (IoT devices, hubs, mobile apps, cloud accounts) into one
queryable knowledge graph, instead of leaving an investigator to manually
cross-reference artifacts pulled from a dozen separate tools.

The codebase in this repository has since moved past what either paper
describes: it now targets the current UCO/CASE 1.5.0 standard rather than the
~0.9.1/0.7.1 versions those papers were written against. See `CHANGELOG.md`
for the full history.

## Why ForensicFlow stands out

- **Event-centric, not artifact-centric.** Every extracted fact - a device
  action, an account login, a sensor trigger - becomes a UCO/CASE
  `EventRecord`, linked by `ObservableRelationship`s to the devices,
  accounts, and people it involves, so an investigator can traverse *why*
  two pieces of evidence are connected, not just that they both exist.
- **Real entity resolution, not just extraction.** An exact-match merge pass
  collapses records the same entity produced across multiple sources (e.g.
  one suspect's email address surfacing from both an Amazon and a NEST
  account), and a from-scratch implementation of Myers' 1986 O(ND) diff
  algorithm drives fuzzy `ownedBy` matching between application account
  handles and real names - each asserted link carries its own
  `core:ConfidenceFacet` score rather than being stated as fact.
- **Schema-verified, not just schema-shaped.** Every property this
  generator emits was checked against the actual UCO/CASE 1.5.0 SHACL
  shapes with `pyshacl` (not just "does this class name exist").
- **Per-source, pluggable extractors.** Amazon Alexa, iSmartAlarm, and NEST
  each get their own `carve()` implementation returning a handful of shared
  record types (`UserBase`, `DeviceBase`, `EventBase`, `ArtifactBase`);
  adding a new evidence source means writing one more extractor, not
  touching the ontology-generation layer.

## The dataset

ForensicFlow's extractors and example data target the
[DFRWS 2018 IoT forensic challenge dataset](https://dfrws.org/forensic-challenges/):
a simulated smart-home crime scene with evidence spread across an Amazon
Echo, a NEST Protect, and an iSmartAlarm security system - exactly the kind
of multi-source, cross-device correlation problem the papers above set out
to address.

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

## Citing

If you use ForensicFlow in your own work, please cite the papers it
accompanies:

```bibtex
@inproceedings{chikul2021ontology,
  title     = {An Ontology Engineering Case Study for Advanced Digital Forensic Analysis},
  author    = {Chikul, Pavel and Bahşi, Hayretdin and Maennel, Olaf},
  booktitle = {Model and Data Engineering: 10th International Conference, MEDI 2021},
  year      = {2021},
  publisher = {Springer},
  doi       = {10.1007/978-3-030-78428-7_6}
}

@inproceedings{chikul2024semantic,
  title     = {The Design and Implementation of a Semantic Web Framework for the Event-Centric Digital Forensics Analysis},
  author    = {Chikul, Pavel and Bahşi, Hayretdin and Maennel, Olaf},
  booktitle = {Proceedings of the 10th International Conference on Information Systems Security and Privacy (ICISSP 2024)},
  year      = {2024},
  publisher = {SCITEPRESS},
  doi       = {10.5220/0012437700003648}
}
```

## License

MIT - see [`LICENSE`](LICENSE).
