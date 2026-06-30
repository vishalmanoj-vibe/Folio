#!/usr/bin/env python3
"""
.agents/generated/sync_docs.py
===============================
Auto-generates two index files from the live codebase:

  .agents/generated/callback_index.md  — every Output ID → owning file + line
  .agents/generated/store_index.md     — every dcc.Store → ID, type, seed value

Usage:
    python .agents/generated/sync_docs.py           # write files
    python .agents/generated/sync_docs.py --dry-run # preview without writing

These files are AUTO-GENERATED. Do NOT hand-edit them.
They are overwritten on every run.

For intent, architecture notes, and access patterns, see the human docs:
  - docs/reference/callback_ownership.md   (authoritative ownership notes)
  - docs/reference/store_contracts.md      (exact JSON shapes + safe .get() patterns)
"""

import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # project root
CALLBACKS_DIR = ROOT / "callbacks"
APP_PY = ROOT / "app.py"
OUT_DIR = ROOT / ".agents" / "generated"

DRY_RUN = "--dry-run" in sys.argv

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Standard string Output:  Output("my-id", "prop")  or  Output('my-id', 'prop')
RE_OUTPUT_STR = re.compile(
    r'Output\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']'
    r"(?:\s*,\s*allow_duplicate\s*=\s*(True|False))?"
)

# Pattern-matched Output:  Output({"type": "x", "index": ...}, "prop")
RE_OUTPUT_DICT = re.compile(
    r'Output\(\s*(\{[^)]+\})\s*,\s*["\']([^"\']+)["\']'
    r"(?:\s*,\s*allow_duplicate\s*=\s*(True|False))?"
)

# dcc.Store with id= on same line
RE_STORE_INLINE = re.compile(
    r'dcc\.Store\(\s*id\s*=\s*["\']([^"\']+)["\']' r'(?:.*?storage_type\s*=\s*["\']([^"\']+)["\'])?'
)

# dcc.Store on its own line (id= on next line)
RE_STORE_OPEN = re.compile(r"dcc\.Store\(")
RE_STORE_ID = re.compile(r'id\s*=\s*["\']([^"\']+)["\']')
RE_STORE_TYPE = re.compile(r'storage_type\s*=\s*["\']([^"\']+)["\']')


# ---------------------------------------------------------------------------
# Callback index generation
# ---------------------------------------------------------------------------


def extract_outputs(filepath: Path) -> list[dict]:
    """Extract all Output declarations from a callback file."""
    results = []
    text = filepath.read_text(encoding="utf-8")

    # Standard string outputs
    for m in RE_OUTPUT_STR.finditer(text):
        # Find line number
        line_no = text[: m.start()].count("\n") + 1
        dup = m.group(3) == "True" if m.group(3) else False
        results.append(
            {
                "id": m.group(1),
                "prop": m.group(2),
                "allow_duplicate": dup,
                "pattern_matched": False,
                "line": line_no,
                "file": filepath.name,
            }
        )

    # Pattern-matched dict outputs
    for m in RE_OUTPUT_DICT.finditer(text):
        line_no = text[: m.start()].count("\n") + 1
        dup = m.group(3) == "True" if m.group(3) else False
        results.append(
            {
                "id": m.group(1).replace("\n", " ").strip(),
                "prop": m.group(2),
                "allow_duplicate": dup,
                "pattern_matched": True,
                "line": line_no,
                "file": filepath.name,
            }
        )

    return results


def build_callback_index() -> str:
    """Generate callback_index.md content."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Callback Output Index — Auto-Generated",
        "",
        f"> **Generated**: {timestamp}  ",
        "> **Do not edit** — run `python .agents/generated/sync_docs.py` to refresh.",
        "> For ownership intent and architecture notes, see `docs/reference/callback_ownership.md`.",
        "",
        "---",
        "",
    ]

    all_outputs: list[dict] = []

    # app.py outputs
    if APP_PY.exists():
        app_outputs = extract_outputs(APP_PY)
        for o in app_outputs:
            o["file"] = "app.py"
        all_outputs.extend(app_outputs)

    # callbacks/*.py outputs
    for cb_file in sorted(CALLBACKS_DIR.glob("*.py")):
        if cb_file.name.startswith("__"):
            continue
        file_outputs = extract_outputs(cb_file)
        all_outputs.extend(file_outputs)

    # Group by file
    by_file: dict[str, list[dict]] = {}
    for o in all_outputs:
        by_file.setdefault(o["file"], []).append(o)

    total = 0
    for filename, outputs in by_file.items():
        if not outputs:
            continue
        lines.append(f"## `{filename}`")
        lines.append("")
        lines.append("| Output ID | Property | Line | Duplicate? | Pattern? |")
        lines.append("|-----------|----------|------|-----------|---------|")
        for o in sorted(outputs, key=lambda x: x["line"]):
            dup_flag = "✓" if o["allow_duplicate"] else ""
            pat_flag = "✓" if o["pattern_matched"] else ""
            lines.append(f"| `{o['id']}` | `{o['prop']}` | {o['line']} | {dup_flag} | {pat_flag} |")
            total += 1
        lines.append("")

    lines.insert(8, f"**Total outputs indexed**: {total} across {len(by_file)} files")
    lines.insert(9, "")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Store index generation
# ---------------------------------------------------------------------------


def extract_stores(filepath: Path) -> list[dict]:
    """Extract dcc.Store definitions from a file."""
    results = []
    text = filepath.read_text(encoding="utf-8")

    # Single pass: find all dcc.Store( calls and scan up to 300 characters for ID and storage type
    for m in RE_STORE_OPEN.finditer(text):
        snippet_start = m.start()
        snippet = text[snippet_start : snippet_start + 300]
        # Truncate to the next dcc.Store( call to prevent attributes leaking from downstream stores
        next_store_idx = snippet.find("dcc.Store(", 10)
        if next_store_idx != -1:
            snippet = snippet[:next_store_idx]

        id_m = RE_STORE_ID.search(snippet)
        if not id_m:
            continue
        line_no = text[: m.start()].count("\n") + 1
        store_id = id_m.group(1)
        type_m = RE_STORE_TYPE.search(snippet)
        storage_type = type_m.group(1) if type_m else "memory"

        # Avoid duplicates
        if any(r["id"] == store_id for r in results):
            continue
        results.append(
            {
                "id": store_id,
                "storage_type": storage_type,
                "line": line_no,
            }
        )

    return results


def build_store_index() -> str:
    """Generate store_index.md content."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Store Index — Auto-Generated",
        "",
        f"> **Generated**: {timestamp}  ",
        "> **Do not edit** — run `python .agents/generated/sync_docs.py` to refresh.",
        "> For exact JSON shapes and safe access patterns, see `docs/reference/store_contracts.md`.",
        "",
        "---",
        "",
    ]

    stores = extract_stores(APP_PY) if APP_PY.exists() else []

    lines.append(f"**Total stores**: {len(stores)}  (all seeded in `app.py`)")
    lines.append("")
    lines.append("| Store ID | Storage Type | Seeded at Line |")
    lines.append("|----------|-------------|----------------|")

    storage_order = {"local": 0, "session": 1, "memory": 2}
    for s in sorted(stores, key=lambda x: (storage_order.get(x["storage_type"], 3), x["id"])):
        lines.append(f"| `{s['id']}` | `{s['storage_type']}` | {s['line']} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Storage Type Reference")
    lines.append("")
    lines.append("| Type | Persists across | Cleared by |")
    lines.append("|------|----------------|-----------|")
    lines.append("| `local` | Browser sessions, refreshes | Manual clear or new device |")
    lines.append("| `session` | Page navigations within tab | Closing the tab |")
    lines.append("| `memory` | Nothing (in-memory only) | Any page refresh |")
    lines.append("| *(default)* | Nothing (same as memory) | Any page refresh |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def write_or_preview(path: Path, content: str, label: str) -> None:
    if DRY_RUN:
        print(f"\n{'=' * 60}")
        print(f"[DRY RUN] Would write: {path.relative_to(ROOT)}")
        print(f"{'=' * 60}")
        print(content[:2000])
        if len(content) > 2000:
            print(f"  ... ({len(content) - 2000} more characters)")
    else:
        path.write_text(content, encoding="utf-8")
        print(f"  ✓ Written: {path.relative_to(ROOT)}  ({len(content.splitlines())} lines)")


def main() -> None:
    if DRY_RUN:
        print("Running in DRY-RUN mode — no files will be written.\n")
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Syncing docs from: {ROOT}\n")

    cb_content = build_callback_index()
    write_or_preview(OUT_DIR / "callback_index.md", cb_content, "callback_index.md")

    store_content = build_store_index()
    write_or_preview(OUT_DIR / "store_index.md", store_content, "store_index.md")

    if not DRY_RUN:
        print("\nDone. Add to git or run before each build cycle.")
        print("Tip: pipe to 'less' to browse large outputs.\n")


if __name__ == "__main__":
    main()
