#!/usr/bin/env bash
# research-publishing-pipeline installer
# Usage: ./setup.sh [target-project-dir]
#
# This script:
# 1. Copies the pipeline to <target>/tools/research-publishing-pipeline/
# 2. Installs the /article slash command to <target>/.claude/commands/
# 3. Installs Python dependencies (pyyaml)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-.}"
TARGET="$(cd "$TARGET" && pwd)"

echo "=== Research Publishing Pipeline Installer ==="
echo "Source:  $SCRIPT_DIR"
echo "Target:  $TARGET"
echo ""

# 1. Copy pipeline
PIPELINE_DIR="$TARGET/tools/research-publishing-pipeline"
if [ -d "$PIPELINE_DIR" ]; then
  echo "⚠  Pipeline directory already exists at $PIPELINE_DIR"
  read -rp "Overwrite? [y/N] " ans
  [ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Aborted."; exit 1; }
  rm -rf "$PIPELINE_DIR"
fi

echo "→ Copying pipeline to $PIPELINE_DIR ..."
mkdir -p "$TARGET/tools"
cp -R "$SCRIPT_DIR" "$PIPELINE_DIR"

# Remove installer artifacts from installed copy
rm -f "$PIPELINE_DIR/setup.sh"
rm -rf "$PIPELINE_DIR/.claude"

# 2. Install slash command
COMMANDS_DIR="$TARGET/.claude/commands"
mkdir -p "$COMMANDS_DIR"
echo "→ Installing /article command to $COMMANDS_DIR ..."
cp "$SCRIPT_DIR/.claude/commands/article.md" "$COMMANDS_DIR/article.md"

# 3. Python dependencies
echo "→ Checking Python dependencies ..."
if python3 -c "import yaml" 2>/dev/null; then
  echo "  pyyaml: OK"
else
  echo "  Installing pyyaml ..."
  pip3 install pyyaml
fi

echo ""
echo "=== Done! ==="
echo ""
echo "Next steps:"
echo "  1. cd $TARGET"
echo "  2. Open Claude Code and type: /article 你的文章題目"
echo ""
echo "Optional customization:"
echo "  - Edit scripts/run_editorial_pass.py to add your name to SELF_CITATION_PATTERNS"
echo "  - Edit specs/style-policy-zh.md to adjust writing style rules"
echo "  - Edit prompts/agent-*.md to customize agent behavior"
