"""Detect identifiers and report character offsets in the original text."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Literal, Protocol

type EntityKind = Literal["PERSON", "ORG", "LOCATION", "CPF", "PHONE", "EMAIL"]
type NamedEntityKind = Literal["PERSON", "ORG", "LOCATION"]

_NER_LABELS: dict[str, NamedEntityKind] = {"PER": "PERSON", "ORG": "ORG", "LOC": "LOCATION"}
_DIRECT_KINDS = {"EMAIL", "CPF", "PHONE"}
_RULES_VERSION = "rules-v1"

_EMAIL_ATOM = r"[\w!#$%&'*+/=?^`{|}~-]+"
_DNS_LABEL = r"[^\W_](?:[^\W_]|-(?=[^\W_]))*"
_EMAIL = re.compile(
    rf"(?<![\w.!#$%&'*+/=?^`{{|}}~-]){_EMAIL_ATOM}(?:\.{_EMAIL_ATOM})*"
    rf"@(?:{_DNS_LABEL}\.)+[^\W\d_]{{2,}}(?![\w-])"
)
_CPF = re.compile(r"(?<!\w)(?:[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}|[0-9]{11})(?!\w)")
_CPF_LABEL = re.compile(r"\bCPF\b[ \t:=#-]*$", re.IGNORECASE)
_AREA_CODE = r"(?:\([1-9][0-9]\)[ \t]*|[1-9][0-9][ \t.-]*)"
_PHONE = re.compile(
    rf"(?<![\w+])(?:(?:\+55[ \t.-]*)?{_AREA_CODE})?"
    r"(?:9[ \t]?[0-9]{4}|[2-5][0-9]{3})[ \t.-]?[0-9]{4}(?!\w)"
)


@dataclass(frozen=True, slots=True)
class Span:
    """Half-open code-point offsets and the type of the detected identifier."""

    start: int
    end: int
    kind: EntityKind


class Detector(Protocol):
    @property
    def version(self) -> str: ...

    def detect(self, text: str) -> list[Span]: ...


class _CombinedDetector:
    def __init__(self, named_entities: Callable[[str], Iterable[Span]], version: str):
        self._named_entities = named_entities
        self.version = version

    def detect(self, text: str) -> list[Span]:
        if not text.strip():
            return []
        candidates = [*_direct_identifiers(text), *self._named_entities(text)]
        # Prefer direct identifiers, then longer matches within each group.
        ordered = sorted(
            candidates,
            key=lambda span: (
                span.kind not in _DIRECT_KINDS,
                -(span.end - span.start),
                span.start,
                span.kind,
            ),
        )
        selected: list[Span] = []
        for span in ordered:
            if not any(span.start < other.end and other.start < span.end for other in selected):
                selected.append(span)
        return sorted(selected, key=lambda span: span.start)


def _direct_identifiers(text: str) -> Iterable[Span]:
    for match in _EMAIL.finditer(text):
        yield Span(*match.span(), "EMAIL")
    for match in _CPF.finditer(text):
        value = match.group()
        # A compact CPF that also has phone syntax needs a label or a valid checksum.
        if (
            _PHONE.fullmatch(value) is None
            or _CPF_LABEL.search(text, max(0, match.start() - 32), match.start())
            or _valid_cpf_checksum(value)
        ):
            yield Span(*match.span(), "CPF")
    for match in _PHONE.finditer(text):
        yield Span(*match.span(), "PHONE")


def _valid_cpf_checksum(value: str) -> bool:
    if len(set(value)) == 1:
        return False
    numbers = [int(digit) for digit in value]
    for length in (9, 10):
        total = sum(number * weight for number, weight in zip(numbers, range(length + 1, 1, -1)))
        if (total * 10 % 11) % 10 != numbers[length]:
            return False
    return True


class FixtureDetector(_CombinedDetector):
    """Use explicit synthetic named-entity fixtures with the normal identifier rules."""

    def __init__(self, entities: Mapping[str, NamedEntityKind] | None = None):
        patterns = [
            (re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE), kind)
            for phrase, kind in (entities or {}).items()
            if phrase.strip()
        ]

        def named_entities(text: str) -> Iterable[Span]:
            for pattern, kind in patterns:
                for match in pattern.finditer(text):
                    yield Span(*match.span(), kind)

        super().__init__(named_entities, version=f"fixture-v1+{_RULES_VERSION}")


def build_detector(model_path: Path) -> Detector:
    """Load Presidio with the explicitly provisioned pt_core_news_lg data directory."""
    model_path = model_path.resolve()
    if not (model_path / "config.cfg").is_file() or not (model_path / "meta.json").is_file():
        raise FileNotFoundError("Provision the local pt_core_news_lg model data directory.")

    import spacy
    from presidio_analyzer.nlp_engine import NerModelConfiguration, SpacyNlpEngine

    class LocalSpacyEngine(SpacyNlpEngine):
        def load(self) -> None:
            # Presidio's default loader may download a missing model. Loading a Path keeps
            # startup local even if the directory is removed after its existence check.
            model = spacy.load(model_path)
            if (
                model.lang != "pt"
                or model.meta.get("name") != "core_news_lg"
                or "ner" not in model.pipe_names
                or not _NER_LABELS.keys() <= set(model.get_pipe("ner").labels)
            ):
                raise ValueError("Expected a Portuguese pt_core_news_lg model with NER labels.")
            self.nlp = {"pt": model}

    engine = LocalSpacyEngine(
        models=[{"lang_code": "pt", "model_name": str(model_path)}],
        ner_model_configuration=NerModelConfiguration(
            model_to_presidio_entity_mapping=dict(_NER_LABELS),
            labels_to_ignore={"MISC"},
            low_score_entity_names=set(),
        ),
    )
    engine.load()
    model_version = engine.get_nlp("pt").meta["version"]

    def named_entities(text: str) -> Iterable[Span]:
        for entity in engine.process_text(text, "pt").entities:
            if entity.label_ in _NER_LABELS.values():
                yield Span(entity.start_char, entity.end_char, entity.label_)

    return _CombinedDetector(
        named_entities,
        version=(
            f"{_RULES_VERSION}+presidio-{package_version('presidio-analyzer')}"
            f"+spacy-{spacy.__version__}+pt_core_news_lg-{model_version}"
        ),
    )
