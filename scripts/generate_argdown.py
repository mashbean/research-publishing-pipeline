#!/usr/bin/env python3
"""Generate Argdown from a v2 argmap YAML file.

The argmap YAML remains the source of truth. This script performs a
deterministic format conversion and does not add claims or rewrite content.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from typing import Any

from lib import resolve_job_dir

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - environment guard
    yaml = None


def strip_html(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"</?(strong|em|span|p|br)\b[^>]*>", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return normalize_space(value)


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def clean_ref(value: str, fallback: str) -> str:
    text = strip_html(value) or fallback
    text = re.sub(r"[\[\]<>]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:96] or fallback


def escape_argdown_text(value: Any) -> str:
    text = strip_html(value)
    text = re.sub(r"\s*\n\s*", " / ", text)
    safe_chars = []
    allowed = set("，。、！？「」『』（）().,-—%")
    for char in text:
        if char.isalnum() or char.isspace() or char in allowed:
            safe_chars.append(char)
        else:
            safe_chars.append(" ")
    return re.sub(r"\s+", " ", "".join(safe_chars)).strip()


def statement(ref: str, text: str, tag: str | None = None) -> str:
    suffix = f" #{tag}" if tag else ""
    return f"[{ref}]: {escape_argdown_text(text)}{suffix}"


def argument(ref: str, parts: list[Any], tag: str | None = None) -> str:
    body = " ".join(escape_argdown_text(part) for part in parts if strip_html(part))
    suffix = f" #{tag}" if tag else ""
    if body:
        return f"<{ref}>: {body}{suffix}"
    return f"<{ref}>:{suffix}"


def relation_tree(core_ref: str, support_refs: list[str], objection_pairs: list[tuple[str, str]]) -> str:
    lines = [f"[{core_ref}]"]
    for ref in support_refs:
        lines.append(f"  + {ref}")
    for objection_ref, reply_ref in objection_pairs:
        lines.append(f"  - {objection_ref}")
        lines.append(f"    - {reply_ref}")
        lines.append(f"  + {reply_ref}")
    return "\n".join(lines)


def frontmatter(data: dict[str, Any]) -> str:
    title = normalize_space(data.get("title") or data.get("slug") or "Argument Map")
    subtitle = normalize_space(data.get("subtitle") or "Argdown export")
    slug = normalize_space(data.get("slug") or "")
    return "\n".join(
        [
            "===",
            f"title: {title}",
            f"subTitle: {subtitle}",
            f"slug: {slug}",
            "author: research-article-pipeline argdown export",
            "model:",
            "  removeTagsFromText: true",
            "===",
        ]
    )


def convert(data: dict[str, Any]) -> str:
    core = data.get("coreThesis") or {}
    core_ref = "Core Thesis"
    accepted_ref = None
    support_refs: list[str] = []
    objection_pairs: list[tuple[str, str]] = []
    sections: list[str] = [frontmatter(data), "# Central Thesis"]

    sections.append(statement(core_ref, core.get("text", ""), "thesis"))

    formal = core.get("formal") or {}
    if formal.get("expression"):
        formal_parts = [
            "Formula:",
            normalize_space(formal.get("expression")),
            f"Caption: {formal.get('caption', '')}" if formal.get("caption") else "",
        ]
        sections.append(argument("Formal Core", formal_parts, "formal"))
        support_refs.append("<Formal Core>")

    distinction = data.get("distinction") or {}
    if distinction.get("accepted"):
        accepted = distinction["accepted"]
        accepted_ref = "Accepted"
        sections.append(statement(accepted_ref, f"{accepted.get('title', '')}. {accepted.get('body', '')}", "accepted"))
        support_refs.append(f"[{accepted_ref}]")
    if distinction.get("rejected"):
        rejected = distinction["rejected"]
        rejected_ref = "Rejected"
        sections.append(statement(rejected_ref, f"{rejected.get('title', '')}. {rejected.get('body', '')}", "rejected"))
        if accepted_ref:
            objection_pairs.append((f"[{rejected_ref}]", f"[{accepted_ref}]"))

    pillar_refs: list[str] = []
    for index, pillar in enumerate(data.get("pillars") or [], start=1):
        title = clean_ref(pillar.get("title", ""), f"Pillar {index}")
        ref = f"P{index}"
        parts = [
            f"Title: {title}",
            f"Section: {pillar.get('section', '')}",
            f"Role: {pillar.get('role', '')}",
            pillar.get("body", ""),
            f"Finding: {pillar.get('finding', '')}" if pillar.get("finding") else "",
            f"Formal: {pillar.get('formal', '')}" if pillar.get("formal") else "",
        ]
        sections.append(argument(ref, parts, "pillar"))
        pillar_refs.append(f"<{ref}>")
    support_refs.extend(pillar_refs)

    chain = data.get("chain") or {}
    if chain.get("steps"):
        ref = "Causal Chain"
        parts = [f"Title: {chain.get('title', '')}"]
        parts.extend(f"{step.get('tag', '')} ({step.get('kind', '')}): {step.get('text', '')}" for step in chain["steps"])
        sections.append(argument(ref, parts, "chain"))
        support_refs.append(f"<{ref}>")

    condition_refs: list[str] = []
    conditions = data.get("conditions") or {}
    if conditions.get("items"):
        conditions_ref = "Deployment Conditions"
        sections.append(statement(conditions_ref, f"{conditions.get('title', '')}. {conditions.get('formalPrelude', '')}", "conditions"))
        support_refs.append(f"[{conditions_ref}]")
        for index, item in enumerate(conditions.get("items") or [], start=1):
            title = clean_ref(item.get("title", ""), f"Condition {index}")
            ref = f"C{index}"
            parts = [
                f"Title: {title}",
                item.get("body", ""),
                f"Formal: {item.get('formal', '')}" if item.get("formal") else "",
            ]
            sections.append(argument(ref, parts, "condition"))
            condition_refs.append(f"<{ref}>")

    border_sections: list[str] = []
    for index, border in enumerate(data.get("borders") or [], start=1):
        title = clean_ref(border.get("title", ""), f"Objection {index}")
        objection_ref = f"Objection {index}"
        reply_ref = f"Reply {index}"
        border_sections.append(statement(objection_ref, f"{title}. {border.get('pivot', '')}", "objection"))
        border_sections.append(argument(reply_ref, [f"Title: {title}", border.get("flip", "")], "reply"))
        objection_pairs.append((f"[{objection_ref}]", f"<{reply_ref}>"))

    conclusion = data.get("conclusion") or {}
    if conclusion.get("paragraphs") or conclusion.get("formalCoda"):
        parts = [*(conclusion.get("paragraphs") or [])]
        if conclusion.get("formalCoda"):
            parts.extend(["Formal Coda:", conclusion["formalCoda"]])
        sections.append(argument("Conclusion", parts, "conclusion"))
        support_refs.append("<Conclusion>")

    sections.insert(2, relation_tree(core_ref, support_refs, objection_pairs))
    if condition_refs:
        sections.append("# Deployment Conditions")
        sections.append(relation_tree(conditions_ref, condition_refs, []))
    if border_sections:
        sections.append("# Objections And Replies")
        sections.extend(border_sections)

    return "\n\n".join(section for section in sections if section).rstrip() + "\n"


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required: run this script with the pipeline Python environment.")
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Argmap YAML did not parse to a mapping: {path}")
    return data


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    job_dir = resolve_job_dir(args.job) if args.job else None
    if args.input:
        input_path = Path(args.input).expanduser().resolve()
    elif job_dir:
        input_path = job_dir / "final" / "argmap.yaml"
    else:
        raise ValueError("Either <job-id-or-path> or --input is required.")

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    elif job_dir:
        output_path = job_dir / "final" / "argument.argdown"
    else:
        output_path = input_path.with_suffix(".argdown")

    return input_path, output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", nargs="?", help="Job id or job directory. Defaults input/output to final/ files.")
    parser.add_argument("--input", help="Explicit argmap YAML input path.")
    parser.add_argument("--output", help="Explicit Argdown output path.")
    args = parser.parse_args()

    try:
        input_path, output_path = resolve_paths(args)
        if not input_path.exists():
            raise FileNotFoundError(f"Argmap YAML not found: {input_path}")
        data = load_yaml(input_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(convert(data))
    except Exception as exc:
        print(f"generate_argdown.py: {exc}", file=sys.stderr)
        return 1

    print(f"Generated Argdown: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
