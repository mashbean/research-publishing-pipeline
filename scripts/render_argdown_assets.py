#!/usr/bin/env python3
"""Render an Argdown file into static HTML/SVG assets."""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from lib import resolve_job_dir
from validate_argdown import find_argdown


def metadata_from_argdown(path: Path) -> dict[str, str]:
    text = path.read_text()
    if not text.startswith("==="):
        return {}

    lines = text.splitlines()
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "===":
            break
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def clean_slug(value: str, fallback: str) -> str:
    value = value.strip() or fallback
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value)
    value = value.strip("-._")
    return value or fallback


def resolve_input(args: argparse.Namespace) -> Path:
    if args.input:
        return Path(args.input).expanduser().resolve()
    if not args.job:
        raise ValueError("Either <job-id-or-path> or --input is required.")
    return resolve_job_dir(args.job) / "final" / "argument.argdown"


def default_output_dir(input_path: Path, args: argparse.Namespace) -> Path:
    if args.output_dir:
        return Path(args.output_dir).expanduser().resolve()
    if args.job:
        return resolve_job_dir(args.job) / "final" / "argdown-render"
    return input_path.parent / "argdown-render"


def run_argdown(argdown_bin: Path, export: str, input_path: Path, output_dir: Path, extra_args: list[str] | None = None) -> None:
    env = os.environ.copy()
    local_bin = str(Path.home() / ".local" / "bin")
    env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"
    result = subprocess.run(
        [
            str(argdown_bin),
            export,
            str(input_path),
            str(output_dir),
            *(extra_args or []),
            "--throwExceptions",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"Argdown {export} export failed for {input_path}")
    print(result.stdout, end="")


def copy_required(source: Path, target: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Expected Argdown output missing: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


STATEMENT_DEFINITION = re.compile(r"^\[([^\]]+)\]:\s*(.*)$")
ARGUMENT_DEFINITION = re.compile(r"^<([^>]+)>:\s*(.*)$")
RELATION_REFERENCE = re.compile(r"^(?P<prefix>\s*(?:(?:\+|-)\s+)?)(?P<open>[\[<])(?P<ref>[^\]>]+)(?P<close>[\]>])\s*$")


def strip_tag(value: str) -> str:
    return re.sub(r"\s+#[A-Za-z0-9_-]+\s*$", "", value).strip()


def clean_summary_label(value: str, fallback: str, limit: int = 34) -> str:
    value = strip_tag(value)
    value = value.replace("「", "").replace("」", "").replace("『", "").replace("』", "")
    value = re.sub(r"[\[\]<>#`*_{}|]", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .,:;-—，。、！？「」『』")
    if len(value) > limit:
        trimmed = value[: max(limit - 3, 1)].rstrip(" .,:;-—，。、！？「」『』")
        space = trimmed.rfind(" ")
        if space >= 12:
            trimmed = trimmed[:space].rstrip(" .,:;-—，。、！？「」『』")
        value = f"{trimmed}..."
    return value or fallback


def title_from_definition(value: str) -> str:
    value = strip_tag(value)
    if not value.startswith("Title "):
        return ""

    title = value.removeprefix("Title ").strip()
    for pattern in [
        r"\s+Section\s+",
        r"\s+Role\s+",
        r"\s+Finding\s+",
        r"\s+Formal\s+",
        r"\s+Caption\s+",
        r"\s+T0\s+",
        r"\s+反論",
    ]:
        title = re.split(pattern, title, maxsplit=1)[0]
    return title.strip()


def first_phrase(value: str) -> str:
    value = strip_tag(value)
    return re.split(r"(?<!\d)[.。](?!\d)", value, maxsplit=1)[0].strip()


def quoted_phrase(value: str) -> str:
    value = strip_tag(value)
    quoted = re.search(r"[「『](.*?)[」』]", value)
    return quoted.group(1).strip() if quoted else ""


def argument_label(ref: str, body: str) -> str:
    title = title_from_definition(body)
    if title:
        if ref.startswith("Reply "):
            return clean_summary_label(f"Reply {title}", ref, 38)
        return clean_summary_label(title, ref, 38)
    if ref in {"Formal Core", "Conclusion"}:
        return ref
    return clean_summary_label(first_phrase(body), ref, 38)


def statement_label(ref: str, body: str) -> str:
    if ref.startswith("Objection"):
        return clean_summary_label(quoted_phrase(body) or first_phrase(body), ref, 38)
    return clean_summary_label(first_phrase(body), ref, 38)


def summary_labels(text: str, metadata: dict[str, str]) -> dict[str, str]:
    labels: dict[str, str] = {}
    if metadata.get("title"):
        labels["Core Thesis"] = clean_summary_label(metadata["title"], "Core Thesis", 38)

    for line in text.splitlines():
        line = line.strip()
        statement_match = STATEMENT_DEFINITION.match(line)
        if statement_match:
            ref, body = statement_match.groups()
            labels.setdefault(ref, statement_label(ref, body))
            continue

        argument_match = ARGUMENT_DEFINITION.match(line)
        if argument_match:
            ref, body = argument_match.groups()
            labels[ref] = argument_label(ref, body)

    return labels


def rewrite_relation_tree(block: str, labels: dict[str, str]) -> str:
    lines: list[str] = []
    for line in block.splitlines():
        match = RELATION_REFERENCE.match(line)
        if not match:
            lines.append(line)
            continue

        ref = match.group("ref")
        label = labels.get(ref, ref)
        lines.append(f"{match.group('prefix')}{match.group('open')}{label}{match.group('close')}")
    return "\n".join(lines)


def summary_argdown_text(path: Path) -> str:
    """Keep only the first relation tree, with article-specific display labels."""
    text = path.read_text()
    labels = summary_labels(text, metadata_from_argdown(path))
    blocks = text.split("\n\n")
    selected: list[str] = []
    for block in blocks:
        if block.startswith("[Core Thesis]\n"):
            selected.append(rewrite_relation_tree(block, labels))
            break
        selected.append(block)
    return "\n\n".join(selected).rstrip() + "\n"


def polished_svg_text(path: Path) -> str:
    """Retheme Graphviz SVG output to fit blog-pro instead of the defaults."""
    svg = path.read_text()
    replacements = {
        'font-family="arial"': 'font-family="Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"',
        'fill="#000000"': 'fill="#2f2a21"',
        'fill="#dadada" stroke="#dadada"': 'fill="#f3eadb" stroke="#d4c0a1"',
        'fill="white"': 'fill="#fffdf7"',
        'stroke="#1b9e77"': 'stroke="#6f8f72"',
        'fill="#1b9e77"': 'fill="#e8f1e8"',
        'stroke="#00ff00"': 'stroke="#6f8f72"',
        'fill="#00ff00"': 'fill="#6f8f72"',
        'stroke="#ff0000"': 'stroke="#b85b57"',
        'fill="#ff0000"': 'fill="#b85b57"',
        'stroke="black"': 'stroke="#c8b794"',
    }
    for before, after in replacements.items():
        svg = svg.replace(before, after)
    svg = svg.replace("<svg ", '<svg class="argdown-summary-map" ')
    return svg


def render(input_path: Path, output_root: Path, slug: str | None = None) -> list[Path]:
    if not input_path.exists():
        raise FileNotFoundError(f"Argdown file not found: {input_path}")

    argdown_bin = find_argdown()
    if not argdown_bin:
        raise RuntimeError("Argdown CLI not found. Install it or set ARGDOWN_BIN.")

    metadata = metadata_from_argdown(input_path)
    resolved_slug = clean_slug(slug or metadata.get("slug", ""), input_path.stem)
    target_dir = output_root / resolved_slug
    stem = input_path.stem

    with tempfile.TemporaryDirectory(prefix="argdown-render.") as temp_name:
        temp_dir = Path(temp_name)
        summary_input = temp_dir / f"{stem}-summary.argdown"
        summary_input.write_text(summary_argdown_text(input_path))

        run_argdown(argdown_bin, "html", input_path, temp_dir)
        run_argdown(
            argdown_bin,
            "map",
            summary_input,
            temp_dir,
            [
                "--format",
                "svg",
                "--statement-selection",
                "top-level",
                "--argument-labels",
                "title",
                "--statement-labels",
                "title",
                "--rankdir",
                "LR",
            ],
        )

        written = [
            target_dir / "index.html",
            target_dir / "argdown.css",
            target_dir / "map.svg",
            target_dir / "argument.argdown",
        ]
        copy_required(temp_dir / f"{stem}.html", written[0])
        copy_required(temp_dir / "argdown.css", written[1])
        written[2].parent.mkdir(parents=True, exist_ok=True)
        written[2].write_text(polished_svg_text(temp_dir / f"{stem}-summary.svg"))
        copy_required(input_path, written[3])

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", nargs="?", help="Job id or job directory. Defaults input to final/argument.argdown.")
    parser.add_argument("--input", help="Explicit .argdown input path.")
    parser.add_argument("--output-dir", help="Directory that will receive <slug>/index.html and <slug>/map.svg.")
    parser.add_argument("--slug", help="Override slug directory name.")
    args = parser.parse_args()

    try:
        input_path = resolve_input(args)
        output_dir = default_output_dir(input_path, args)
        written = render(input_path, output_dir, args.slug)
    except Exception as exc:
        print(f"render_argdown_assets.py: {exc}", file=sys.stderr)
        return 1

    for path in written:
        print(f"Rendered Argdown asset: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
