"""Verifier-first constraint-field reasoning substrate."""

from .examples import EXAMPLE_CONCEPT_FIELDS, get_example_concept_field
from .model import (
    CONSTRAINT_FIELD_PRIMITIVES,
    ConceptField,
    FieldItem,
    compare_concept_fields,
    create_concept_field,
    export_receipt,
    field_signature,
    verify_analogy,
)

__all__ = [
    "CONSTRAINT_FIELD_PRIMITIVES",
    "EXAMPLE_CONCEPT_FIELDS",
    "ConceptField",
    "FieldItem",
    "compare_concept_fields",
    "create_concept_field",
    "export_receipt",
    "field_signature",
    "get_example_concept_field",
    "verify_analogy",
]
