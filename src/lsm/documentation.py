"""Deterministic, redacted projections; no filesystem or evidence authentication."""

import unicodedata

from lsm.security import redact
from lsm.validation import validate_model

_WARNING = (
    "Generated from model declarations, not independently verified documentation. "
    "Origin and verification are model metadata; even 'verified' does not authenticate "
    "evidence or prove behavior. Missing links indicate model gaps, not absent behavior."
)


def _plain(value) -> str:
    """Flatten controls, including Unicode bidi/format controls, before escaping."""
    return "".join(
        f" U+{ord(char):04X} " if unicodedata.category(char).startswith("C") else char
        for char in str(value)
    )


def _md(value) -> str:
    # Encode punctuation rather than permitting Markdown links, HTML or code fences.
    return "".join(
        char if char.isalnum() or char == " " else f"&#{ord(char)};" for char in _plain(value)
    )


def _mermaid(value) -> str:
    # Do not allow Mermaid entity decoding to reintroduce quotes or HTML controls.
    return "".join(
        char if char.isascii() and (char.isalnum() or char in " ._:-") else f" U+{ord(char):04X} "
        for char in _plain(value)
    )


def _citation(entity, escape=_md) -> str:
    provenance = entity["provenance"]
    parts = [
        f"origin={provenance['origin']}",
        f"verification={provenance['verification']} (model declaration)",
        f"source={provenance['source']}",
        "evidence=" + ", ".join(sorted(entity.get("evidence", []))),
    ]
    if "rationale" in provenance:
        parts.append("rationale=" + provenance["rationale"])
    return escape("; ".join(parts))


def _node(entity) -> str:
    return (
        f"{_md(entity['id'])}: {_md(entity['title'])} ({_md(entity['type'])}; {_citation(entity)})"
    )


def _edge(entity) -> str:
    return (
        f"{_md(entity['id'])}: {_md(entity['source'])} "
        f"— {_md(entity['type'])} → {_md(entity['target'])}; {_citation(entity)}"
    )


def _details(entity) -> list[str]:
    lines = [f"- {_node(entity)}"]
    for field in (
        "version",
        "description",
        "approval",
        "owner",
        "uri",
        "commit",
        "timestamp",
        "confidence",
        "acceptance_criteria",
        "constraints",
        "open_questions",
    ):
        if field not in entity:
            continue
        values = entity[field] if isinstance(entity[field], list) else [entity[field]]
        for value in values:
            lines.append(f"  - {_md(field)}: {_md(value)}; {_citation(entity)}")
    return lines


def render_docs(model: dict) -> dict[str, str]:
    """Return five UTF-8-ready documents without mutation or filesystem access.

    Validate before redaction. Invalid input raises a deliberately generic error so
    schema diagnostics cannot accidentally disclose input secrets.
    """
    if validate_model(model):
        raise ValueError("Cannot render documentation: invalid model")
    safe = redact(model)
    # Keep raw identifiers only as private lookup keys: redaction can collapse IDs.
    nodes = {raw["id"]: clean for raw, clean in zip(model["nodes"], safe["nodes"], strict=True)}
    ordered = sorted(nodes)
    edges = sorted(zip(model["edges"], safe["edges"], strict=True), key=lambda pair: pair[0]["id"])
    index = [
        f"# {_md(safe['model']['title'])}",
        "",
        _WARNING,
        "",
        f"Model metadata: {_md(safe['model']['id'])}; schema {_md(safe['schema_version'])}.",
        "The model title and ID are supplied metadata, not independently sourced claims.",
        "",
        "## Views",
        "",
        "- [Context diagram](context.mmd)",
        "- [Component diagram](components.mmd)",
        "- [Traceability](traceability.md)",
        "- [Onboarding](onboarding.md)",
        "",
        "## Entity inventory",
        "",
    ]
    for identifier in ordered:
        index.extend(_details(nodes[identifier]))
    index.extend(["", "## Relation inventory", ""])
    index.extend(f"- {_edge(clean)}" for _, clean in edges)
    if not edges:
        index.append("No relations recorded in this model.")

    def diagram(types):
        selected = {key for key in ordered if nodes[key]["type"] in types}
        names = {key: f"n{position:04d}" for position, key in enumerate(ordered, 1)}
        lines = ["%% " + _WARNING, "flowchart LR"]
        for key in ordered:
            if key not in selected:
                continue
            node = nodes[key]
            label = _mermaid(f"{node['id']}: {node['title']} ({node['type']})")
            lines.append(f'  {names[key]}["{label}; {_citation(node, _mermaid)}"]')
        for raw, clean in edges:
            if raw["source"] in selected and raw["target"] in selected:
                label = _mermaid(f"{clean['id']}: {clean['type']}")
                lines.append(
                    f'  {names[raw["source"]]} -->|"{label}; '
                    f'{_citation(clean, _mermaid)}"| {names[raw["target"]]}'
                )
        if not selected:
            lines.append("  %% No matching nodes recorded in this model.")
        return "\n".join(lines) + "\n"

    trace = ["# Requirement traceability", "", _WARNING, ""]
    requirements = [key for key in ordered if nodes[key]["type"] == "requirement"]
    for requirement in requirements:
        trace.extend([f"## {_md(nodes[requirement]['id'])}", ""])
        trace.extend(_details(nodes[requirement]))
        # Follow inverse satisfies and forward implemented_by only. Dependencies,
        # supersession and decision links do not imply requirement implementation.
        reached = {requirement}
        paths = {}
        queue = [requirement]
        for current in queue:
            for raw, clean in edges:
                target = None
                if raw["source"] == current and raw["type"] == "implemented_by":
                    target = raw["target"]
                elif raw["target"] == current and raw["type"] == "satisfies":
                    target = raw["source"]
                if target is not None and target not in reached:
                    reached.add(target)
                    paths[target] = paths.get(current, []) + [clean]
                    queue.append(target)
        trace.extend(["", "### Implementation links", ""])
        implementations = [key for key in sorted(reached) if nodes[key]["type"] == "implementation"]
        for key in implementations:
            trace.append(f"- {_node(nodes[key])}")
            trace.extend(f"  - Path: {_edge(edge)}" for edge in paths[key])
        if not implementations:
            trace.append(
                "Gap: no implementation node reachable by explicit satisfies/implemented_by links."
            )
        trace.extend(["", "### Verification links", ""])
        checks = [
            (raw, clean)
            for raw, clean in edges
            if raw["source"] in reached and raw["type"] == "verified_by"
        ]
        for raw, clean in checks:
            trace.append(f"- {_node(nodes[raw['target']])}")
            trace.extend(f"  - Path: {_edge(edge)}" for edge in paths.get(raw["source"], []))
            trace.append(f"  - {_edge(clean)}")
        if not checks:
            trace.append("Gap: no verified_by test/evidence links recorded along these paths.")
        trace.extend(
            [
                "",
                "Linked tests/evidence are not proof of execution or passing results. "
                "Evidence authenticity and behavior remain unassessed by this renderer.",
                "",
            ]
        )
    if not requirements:
        trace.append("No requirements recorded; implementation and test coverage are unknown.")

    onboarding = [
        "# Onboarding",
        "",
        _WARNING,
        "",
        "Start with the [inventory](index.md) and "
        "[requirement traceability](traceability.md). Review sources before changing intent.",
        "",
    ]
    for heading, types in (
        ("Components and repositories", {"component", "repository", "interface"}),
        ("Decisions overview", {"decision"}),
    ):
        onboarding.extend([f"## {heading}", ""])
        matches = [nodes[key] for key in ordered if nodes[key]["type"] in types]
        for node in matches:
            onboarding.extend(_details(node))
        if not matches:
            onboarding.append(
                "None recorded in this model; no conclusion about the system follows."
            )
        onboarding.append("")
    onboarding.extend(["## Dependencies, repository boundaries and decision links", ""])
    relevant = [
        clean
        for _, clean in edges
        if clean["type"] in {"depends_on", "belongs_to", "exposes", "decided_by"}
    ]
    onboarding.extend(f"- {_edge(edge)}" for edge in relevant)
    if not relevant:
        onboarding.append("No dependency, ownership or decision relations recorded.")
    onboarding.extend(
        [
            "",
            "## Uncertainty and next checks",
            "",
            "Review pending approvals and open questions in the inventory. "
            "Missing questions do not establish certainty. No repository was inspected, "
            "test run, source URI fetched or evidence authenticated by this renderer. "
            "Seek human approval before changing requirements or consequential architecture.",
        ]
    )
    return {
        "index.md": "\n".join(index) + "\n",
        "context.mmd": diagram({"repository", "component"}),
        "components.mmd": diagram({"repository", "component", "interface", "implementation"}),
        "traceability.md": "\n".join(trace) + "\n",
        "onboarding.md": "\n".join(onboarding) + "\n",
    }
