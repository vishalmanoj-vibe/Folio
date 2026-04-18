#!/bin/bash

OUTPUT_FILE="project_dump.md"

echo "# Project Export" > "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# ─────────────────────────────────────────────
# FILE STRUCTURE
# ─────────────────────────────────────────────
echo "## File Structure" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

find . \
  -type f -name "*.py" \
  -not -path "*/__pycache__/*" \
  -not -path "*/.git/*" \
  -not -path "*/venv/*" \
  -not -path "*/.venv/*" \
  -not -path "*/node_modules/*" \
| sed 's|^\./||' \
| sort >> "$OUTPUT_FILE"

echo "" >> "$OUTPUT_FILE"

# ─────────────────────────────────────────────
# CODE DUMP
# ─────────────────────────────────────────────
echo "## Code" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

find . \
  -type f -name "*.py" \
  -not -path "*/__pycache__/*" \
  -not -path "*/.git/*" \
  -not -path "*/venv/*" \
  -not -path "*/.venv/*" \
  -not -path "*/node_modules/*" \
| sort | while read file; do

  echo "" >> "$OUTPUT_FILE"
  echo "==================================================" >> "$OUTPUT_FILE"
  echo "FILE: $file" >> "$OUTPUT_FILE"
  echo "==================================================" >> "$OUTPUT_FILE"
  echo '```python' >> "$OUTPUT_FILE"

  cat "$file" >> "$OUTPUT_FILE"

  echo '```' >> "$OUTPUT_FILE"

done

echo "" >> "$OUTPUT_FILE"
echo "✅ Project dump complete: $OUTPUT_FILE"