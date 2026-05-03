#!/usr/bin/env python3
"""Run external deep research via Anthropic API with web_search + adaptive thinking.

This is the F-tier automation for the article pipeline: instead of manually
pasting prompts into claude.ai's Research mode, this script calls Claude Opus 4.7
directly with web_search + extended thinking + task budgets, streams the result,
and saves it to <job-dir>/raw/external-deep-research-claude.md.

Usage:
    pip3 install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 scripts/run_external_deep_research.py 2026-05-02-accountability-without-identification

Optional flags:
    --effort {low,medium,high,xhigh,max}   default: xhigh (best for agentic research on Opus 4.7)
    --max-tokens N                         default: 64000
    --max-uses N                           default: 30 (per server tool)
    --task-budget N                        default: 250000 (whole agentic loop, min 20000)
    --no-task-budget                       disable task_budget beta header
    --prompt-file PATH                     override default prompt lookup
    --output PATH                          override output path
    --no-stream                            disable streaming (only for very short prompts)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def load_dotenv(repo_root: Path) -> None:
    """Auto-source .env from repo roots so the script works without shell setup.

    Looks at the AI-Agent root and the pipeline root. Does not overwrite vars
    already set in the environment.
    """
    candidates = [
        repo_root.parent.parent / ".env",  # /Users/.../AI-Agent/.env
        repo_root / ".env",                # /Users/.../research-publishing-pipeline/.env
    ]
    for env_path in candidates:
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # Empty-string env vars (sandbox-injected) count as unset for our purposes
            if key and not os.environ.get(key):
                os.environ[key] = value

DEFAULT_MODEL = "claude-opus-4-7"
DEFAULT_EFFORT = "xhigh"
DEFAULT_MAX_TOKENS = 64_000
DEFAULT_MAX_USES = 30
DEFAULT_TASK_BUDGET = 250_000

# Lookup order for prompt files
PROMPT_FALLBACKS = [
    "external-claude-ai-deep-research.md",
    "deep-research-prompt.md",
]


def resolve_prompt(job_dir: Path, override: Path | None) -> Path:
    if override:
        if not override.exists():
            sys.exit(f"Error: prompt file not found: {override}")
        return override
    for name in PROMPT_FALLBACKS:
        p = job_dir / "prompts" / name
        if p.exists():
            return p
    sys.exit(
        f"Error: no prompt file in {job_dir / 'prompts'}; "
        f"expected one of {PROMPT_FALLBACKS}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run external deep research via Anthropic API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("job_id", help="Job ID (e.g. 2026-05-02-...)")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model ID (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--effort",
        default=DEFAULT_EFFORT,
        choices=["low", "medium", "high", "xhigh", "max"],
        help=(
            "Thinking + tool-use depth on Opus 4.7 (replaces budget_tokens). "
            f"default: {DEFAULT_EFFORT}"
        ),
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Max output tokens (default: {DEFAULT_MAX_TOKENS})",
    )
    parser.add_argument(
        "--max-uses",
        type=int,
        default=DEFAULT_MAX_USES,
        help=f"Max web_search/web_fetch invocations each (default: {DEFAULT_MAX_USES})",
    )
    parser.add_argument(
        "--task-budget",
        type=int,
        default=DEFAULT_TASK_BUDGET,
        help=(
            "Total tokens for full agentic loop; minimum 20000. "
            f"default: {DEFAULT_TASK_BUDGET}"
        ),
    )
    parser.add_argument(
        "--no-task-budget",
        action="store_true",
        help="Disable task_budget beta header (use plain max_tokens ceiling only)",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=None,
        help="Override prompt file path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override output path (default: <job>/raw/external-deep-research-claude.md)",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming (NOT recommended; SDK times out for max_tokens > ~16000)",
    )
    parser.add_argument(
        "--system",
        default=(
            "You are a deep research agent for an academic publishing pipeline. "
            "Produce rigorous, citation-rich research packs suitable for inclusion "
            "in a doctoral dissertation. Cite primary sources with full URL/DOI; "
            "distinguish A-grade peer-reviewed sources from B/C-grade. "
            "Preserve <!-- SECTION: ... --> markers required by the pipeline.\n\n"
            "CRITICAL OUTPUT REQUIREMENT — DO NOT VIOLATE:\n"
            "1. Stream the ENTIRE research pack as text content blocks in your response.\n"
            "2. DO NOT save your output to any file (no Python file writes, no shell commands).\n"
            "3. DO NOT use a sandbox or code-execution environment to construct large outputs.\n"
            "4. Your text response IS the deliverable. Output the full markdown directly.\n"
            "5. If the response would exceed the token limit, end with the literal token "
            "<<TO_BE_CONTINUED>> so the caller can request continuation. Never silently "
            "truncate or save-to-file.\n"
            "Web search is the ONLY tool you should use, and only for retrieving sources."
        ),
        help="System prompt (default: academic research framing with strict streaming instruction)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent.resolve()
    load_dotenv(repo_root)

    try:
        from anthropic import Anthropic
    except ImportError:
        sys.exit(
            "Error: 'anthropic' package not installed.\n"
            "Run: pip3 install anthropic"
        )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "Error: ANTHROPIC_API_KEY not found in env or .env files.\n"
            "Add to /Users/mashbean/Documents/AI-Agent/.env:\n"
            "  ANTHROPIC_API_KEY=sk-ant-..."
        )

    job_dir = repo_root / "jobs" / args.job_id
    if not job_dir.exists():
        sys.exit(f"Error: job not found: {job_dir}")

    prompt_path = resolve_prompt(job_dir, args.prompt_file)
    output_path = args.output or (job_dir / "raw" / "external-deep-research-claude.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prompt_text = prompt_path.read_text()

    client = Anthropic()

    # Build request — Opus 4.7 uses adaptive thinking + effort, not budget_tokens
    output_config: dict = {"effort": args.effort}
    betas: list[str] = []
    if not args.no_task_budget:
        output_config["task_budget"] = {
            "type": "tokens",
            "total": max(20_000, args.task_budget),
        }
        betas.append("task-budgets-2026-03-13")

    request_kwargs: dict = {
        "model": args.model,
        "max_tokens": args.max_tokens,
        # display="summarized" makes thinking visible in stream (default is "omitted" on 4.7)
        "thinking": {"type": "adaptive", "display": "summarized"},
        "output_config": output_config,
        # Tool selection note (since 2026-05-03):
        # web_search_20260209 includes built-in dynamic filtering that runs a
        # server-side Python REPL. Article 01 (2026-05-02) lost ~46K output tokens
        # to that sandbox when the model wrote its final research pack into a
        # sandbox file we couldn't export. Switching to web_search_20250305
        # removes the Python sandbox entirely. Only web_search is needed for
        # research; we do not include code_execution_20260120 to avoid giving
        # the model another way to leak output to a sandbox file.
        "tools": [
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": args.max_uses,
            },
        ],
        "system": [
            {
                "type": "text",
                "text": args.system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        ],
    }

    # Telemetry
    print("→ External deep research", file=sys.stderr)
    print(f"  Job:        {args.job_id}", file=sys.stderr)
    print(f"  Model:      {args.model}", file=sys.stderr)
    print(f"  Effort:     {args.effort}", file=sys.stderr)
    print(f"  Max tokens: {args.max_tokens:,}", file=sys.stderr)
    print(f"  Max search: {args.max_uses} per tool (web_search + web_fetch)", file=sys.stderr)
    if "task_budget" in output_config:
        print(f"  Task budg:  {output_config['task_budget']['total']:,} tokens", file=sys.stderr)
    print(f"  Prompt:     {prompt_path.relative_to(repo_root)}", file=sys.stderr)
    print(f"  Output:     {output_path.relative_to(repo_root)}", file=sys.stderr)
    print(f"  Streaming:  {'disabled' if args.no_stream else 'enabled'}", file=sys.stderr)
    print("", file=sys.stderr)

    text_chunks: list[str] = []
    thinking_chunks: list[str] = []
    web_searches = 0
    web_fetches = 0
    # Sandbox-leak detector. Set when the model attempts to use code execution
    # or any tool that could write output to a sandbox file we can't export.
    # Article 01 (2026-05-02) lost ~46K output tokens this way; the new default
    # forbids these tools but we still detect violations defensively.
    sandbox_leak_warnings: list[str] = []
    SANDBOX_TOOL_NAMES = {
        "code_execution",       # code_execution_20260120
        "bash",                 # general bash sandbox
        "text_editor",          # str_replace_based_edit_tool
        "container_upload",     # output via files-api
    }
    SANDBOX_BLOCK_TYPES = {
        "server_tool_use",       # only flag when name in SANDBOX_TOOL_NAMES
        "bash_code_execution_tool_result",
        "code_execution_tool_result",
        "text_editor_code_execution_tool_result",
        "container_upload",
    }

    def _detect_sandbox_block(block) -> str | None:
        """Return a warning string if this block indicates sandbox file output."""
        btype = getattr(block, "type", None)
        if btype == "server_tool_use":
            name = getattr(block, "name", None)
            if name in SANDBOX_TOOL_NAMES:
                return f"server_tool_use({name})"
            return None
        if btype in SANDBOX_BLOCK_TYPES and btype != "server_tool_use":
            return btype
        return None

    if args.no_stream:
        method = client.beta.messages.create if betas else client.messages.create
        kwargs = dict(request_kwargs)
        if betas:
            kwargs["betas"] = betas
        response = method(**kwargs)
        for block in response.content:
            btype = block.type
            if btype == "text":
                text_chunks.append(block.text)
            elif btype == "thinking":
                thinking_chunks.append(block.thinking or "")
            elif btype == "server_tool_use":
                name = getattr(block, "name", None)
                if name == "web_search":
                    web_searches += 1
                elif name == "web_fetch":
                    web_fetches += 1
            warning = _detect_sandbox_block(block)
            if warning:
                sandbox_leak_warnings.append(warning)
        usage = response.usage
    else:
        stream_method = client.beta.messages.stream if betas else client.messages.stream
        kwargs = dict(request_kwargs)
        if betas:
            kwargs["betas"] = betas
        with stream_method(**kwargs) as stream:
            for event in stream:
                etype = event.type
                if etype == "content_block_start":
                    block = event.content_block
                    btype = getattr(block, "type", None)
                    if btype == "server_tool_use":
                        name = getattr(block, "name", None)
                        if name == "web_search":
                            web_searches += 1
                            print(
                                f"  [web_search #{web_searches}]",
                                file=sys.stderr,
                                flush=True,
                            )
                        elif name == "web_fetch":
                            web_fetches += 1
                            print(
                                f"  [web_fetch #{web_fetches}]",
                                file=sys.stderr,
                                flush=True,
                            )
                    warning = _detect_sandbox_block(block)
                    if warning:
                        sandbox_leak_warnings.append(warning)
                        print(
                            f"  ⚠️  SANDBOX-LEAK WARNING: model attempted {warning}. "
                            "Output may be saved to a sandbox file we cannot export. "
                            "See run_external_deep_research.py header note for context.",
                            file=sys.stderr,
                            flush=True,
                        )
                elif etype == "content_block_delta":
                    delta = event.delta
                    dtype = getattr(delta, "type", None)
                    if dtype == "text_delta":
                        text_chunks.append(delta.text)
                        print(delta.text, end="", flush=True)
                    elif dtype == "thinking_delta":
                        thinking_chunks.append(delta.thinking)
            final = stream.get_final_message()
            usage = final.usage
        print("", file=sys.stderr)

    # Save outputs
    output_path.write_text("".join(text_chunks))
    if thinking_chunks:
        thinking_path = output_path.with_suffix(".thinking.md")
        thinking_path.write_text("".join(thinking_chunks))
    else:
        thinking_path = None

    print("", file=sys.stderr)
    if sandbox_leak_warnings:
        print(
            "⚠️  SANDBOX-LEAK WARNING — output may be incomplete:",
            file=sys.stderr,
        )
        for w in sandbox_leak_warnings:
            print(f"     • {w}", file=sys.stderr)
        print(
            "     The model attempted to use a sandbox tool. Tokens routed to a "
            "sandbox file would not appear in the saved .md. Check the file "
            "size against `Output tokens` below — a large gap suggests a leak.",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
    print("✓ Done", file=sys.stderr)
    print(f"  web_search calls: {web_searches}", file=sys.stderr)
    print(f"  web_fetch calls:  {web_fetches}", file=sys.stderr)
    print(f"  Sandbox leaks:    {len(sandbox_leak_warnings)}", file=sys.stderr)
    print(f"  Input tokens:     {usage.input_tokens:,}", file=sys.stderr)
    print(
        f"  Cache creation:   {getattr(usage, 'cache_creation_input_tokens', 0):,}",
        file=sys.stderr,
    )
    print(
        f"  Cache read:       {getattr(usage, 'cache_read_input_tokens', 0):,}",
        file=sys.stderr,
    )
    print(f"  Output tokens:    {usage.output_tokens:,}", file=sys.stderr)
    print(f"  → {output_path}", file=sys.stderr)
    if thinking_path:
        print(f"  → {thinking_path}", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        "Next: review the output and integrate via\n"
        f"  python3 scripts/run_deep_research.py {args.job_id} integrate",
        file=sys.stderr,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
