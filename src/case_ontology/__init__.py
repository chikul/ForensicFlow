"""
case_ontology package.

Builds a UCO/CASE-compliant RDF graph (rdflib) from the plain-Python
objects produced by the extractors in src/extractors (UserBase,
DeviceBase, EventBase, ArtifactBase).
"""
from .graph_builder import CaseGraphBuilder
from .myers_diff import myers_diff, similarity_ratio

__all__ = ["CaseGraphBuilder", "myers_diff", "similarity_ratio"]
