#!/usr/bin/env python3
"""yt-summarize: convert YouTube transcripts and synthesize via NotebookLM."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = SCRIPT_DIR / "youtube_summary"

CLASSIFICATION_PROMPT = (
    "Analyze all sources and respond in exactly this format with no extra text:\n"
    "TYPE: <one of: tutorial, lecture, interview, narrative, opinion, mixed>\n"
    "THEMES: <comma-separated list of 4-6 key themes>\n\n"
    "TYPE definitions:\n"
    "- tutorial: how-to, step-by-step, actionable techniques, workflows\n"
    "- lecture: conceptual frameworks, theory, structured education\n"
    "- interview: conversation-driven, multiple speakers, perspectives\n"
    "- narrative: story, journey, case study, chronological arc\n"
    "- opinion: argument-driven, thesis, persuasion, critique\n"
    "- mixed: combination of the above types"
)

VALID_TYPES = {"tutorial", "lecture", "interview", "narrative", "opinion", "mixed"}

PROMPT_LIBRARY = {
    "tutorial": (
        "Synthesize all sources into a practical reference note. Structure it as:\n"
        "1. A short overview paragraph explaining what this teaches and who it is for\n"
        "2. Step-by-step procedures or workflows, grouped by phase or stage\n"
        "3. Key techniques, tools, or methods — wrap named techniques, tools, "
        "frameworks, and concepts in [[wikilinks]]\n"
        "4. Common mistakes or edge cases if mentioned\n\n"
        "Write for fast re-reading. No filler. Use concrete language. "
        "No intro or outro sentences about the note itself."
    ),
    "lecture": (
        "Synthesize all sources into a structured study note. Structure it as:\n"
        "1. A short summary of the central thesis or framework\n"
        "2. Core concepts and definitions — wrap concept names in [[wikilinks]]\n"
        "3. Frameworks, models, or mental models with explanations\n"
        "4. Key arguments or evidence supporting the main ideas\n"
        "5. Implications or applications\n\n"
        "Write densely. Remove examples that don't add new information. "
        "No intro or outro sentences about the note itself."
    ),
    "interview": (
        "Synthesize all sources into a perspective-map note. Structure it as:\n"
        "1. A short context paragraph — who is speaking and what domain this covers\n"
        "2. Key insights organized by theme, not by speaker — "
        "wrap named concepts and frameworks in [[wikilinks]]\n"
        "3. Points of agreement across speakers (if multiple sources)\n"
        "4. Tensions or disagreements between sources\n"
        "5. Standout claims worth remembering (paraphrase, do not copy verbatim)\n\n"
        "Write for synthesis, not transcription. "
        "No intro or outro sentences about the note itself."
    ),
    "narrative": (
        "Synthesize all sources into a case-study note. Structure it as:\n"
        "1. Context — the situation or challenge being documented\n"
        "2. Chronological arc or key turning points — wrap named projects, people, "
        "tools, and concepts in [[wikilinks]]\n"
        "3. Decisions made and why\n"
        "4. Outcomes and what they reveal\n"
        "5. Lessons extracted — what is generalizable vs context-specific\n\n"
        "Write for pattern recognition, not story recall. "
        "No intro or outro sentences about the note itself."
    ),
    "opinion": (
        "Synthesize all sources into an argument map. Structure it as:\n"
        "1. The central claim or thesis in one sentence\n"
        "2. Main supporting arguments — each as a header with 1-2 sentences of evidence\n"
        "3. Counterarguments acknowledged in the sources (if any)\n"
        "4. Key terms and positions — wrap named concepts in [[wikilinks]]\n"
        "5. Strength of the argument based only on what the sources provide\n\n"
        "Write critically. Separate claim from evidence. "
        "No intro or outro sentences about the note itself."
    ),
    "mixed": (
        "Synthesize all sources into one comprehensive study note. "
        "Organize by theme, remove repetition, and write with headers for major themes. "
        "Use [[wikilinks]] around key concepts, named frameworks, tools, and proper nouns "
        "worth connecting to other notes. "
        "Write for re-reading, not first exposure. "
        "No intro or outro sentences about the note itself."
    ),
}


def extract_title(txt_path: Path) -> str:
    name = txt_path.stem
    if name.endswith(" - YouTube"):
        name = name[: -len(" - YouTube")]
    return name


def to_kebab(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"[\s_]+", "-", title)
    title = re.sub(r"-{2,}", "-", title)
    result = title.strip("-")
    return result if result else "untitled"


def convert_txt_to_md(txt_path: Path, topic_dir: Path) -> Path:
    resources_dir = topic_dir / "topic-resources"
    resources_dir.mkdir(exist_ok=True)
    title = extract_title(txt_path)
    md_path = resources_dir / (to_kebab(title) + ".md")
    if md_path.exists():
        print(f"  [skip] {md_path.name} already exists")
        return md_path
    content = txt_path.read_text(encoding="utf-8", errors="replace")
    md_path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
    print(f"  [converted] {txt_path.name} → {md_path.name}")
    return md_path


def _run_notebooklm(args: list[str]) -> dict:
    result = subprocess.run(
        ["notebooklm"] + args + ["--json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"notebooklm error: {result.stderr.strip()}")
    return json.loads(result.stdout.strip())


def _notebook_exists(notebook_id: str) -> bool:
    try:
        data = _run_notebooklm(["list"])
        notebooks = data.get("notebooks", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        ids = [n.get("id", "") for n in notebooks]
        return notebook_id in ids
    except Exception:
        return False


def get_or_create_notebook(topic: str, topic_dir: Path) -> str:
    id_file = topic_dir / "notebook-id.txt"

    if id_file.exists():
        notebook_id = id_file.read_text().strip()
        if _notebook_exists(notebook_id):
            print(f"  [notebook] reusing existing notebook for '{topic}'")
            return notebook_id
        print(f"  [notebook] stored ID not found in NotebookLM — recreating")

    print(f"  [notebook] creating new notebook '{topic}'")
    data = _run_notebooklm(["create", topic])
    notebook_id = data["notebook"]["id"]
    id_file.write_text(notebook_id)
    print(f"  [notebook] created {notebook_id}")
    return notebook_id


def _list_sources(notebook_id: str) -> list[dict]:
    result = subprocess.run(
        ["notebooklm", "source", "list", "-n", notebook_id, "--json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  [warn] could not list sources: {result.stderr.strip()} — dedup skipped, all files will be uploaded", file=sys.stderr)
        return []
    data = json.loads(result.stdout.strip())
    return data.get("sources", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])


def _upload_source(notebook_id: str, md_path: Path, title: str) -> None:
    result = subprocess.run(
        ["notebooklm", "source", "add", "-n", notebook_id,
         "--title", title, str(md_path), "--json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    data = json.loads(result.stdout.strip()) if result.stdout.strip() else {}
    source_id = data.get("source", {}).get("id")
    if source_id:
        subprocess.run(
            ["notebooklm", "source", "wait", "-n", notebook_id, source_id],
            capture_output=True,
        )


def sync_sources(notebook_id: str, topic_dir: Path) -> None:
    existing = {s.get("title", "") for s in _list_sources(notebook_id)}
    resources_dir = topic_dir / "topic-resources"
    md_files = sorted(resources_dir.glob("*.md")) if resources_dir.exists() else []

    for md_path in md_files:
        first_line = md_path.read_text(encoding="utf-8").split("\n")[0]
        title = re.sub(r'^#+\s*', '', first_line).strip()
        if title in existing:
            print(f"  [skip] '{title}' already in notebook")
            continue
        print(f"  [upload] {md_path.name}")
        try:
            _upload_source(notebook_id, md_path, title)
            print(f"  [ready] '{title}'")
        except Exception as e:
            print(f"  [error] failed to upload '{md_path.name}': {e}", file=sys.stderr)


def _run_ask(notebook_id: str, prompt: str) -> str:
    result = subprocess.run(
        ["notebooklm", "ask", "-n", notebook_id, "--new", "--yes", prompt],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"notebooklm ask failed: {result.stderr.strip()}")
    return result.stdout.strip()


def classify_content(notebook_id: str) -> tuple[str, list[str]]:
    print("  [classify] running pre-synthesis classification...")
    try:
        raw = _run_ask(notebook_id, CLASSIFICATION_PROMPT)
    except Exception as e:
        print(f"  [warn] classification failed: {e} — falling back to 'mixed'", file=sys.stderr)
        return "mixed", []

    content_type = "mixed"
    themes: list[str] = []

    type_match = re.search(r"TYPE:\s*(\w+)", raw, re.IGNORECASE)
    if type_match:
        candidate = type_match.group(1).lower()
        if candidate in VALID_TYPES:
            content_type = candidate

    themes_match = re.search(r"THEMES:\s*(.+)", raw, re.IGNORECASE)
    if themes_match:
        themes = [t.strip() for t in themes_match.group(1).split(",") if t.strip()]

    print(f"  [classify] type={content_type}, themes={themes or '—'}")
    return content_type, themes


def synthesize(notebook_id: str, topic_dir: Path, topic: str, content_type: str, themes: list[str]) -> Path:
    prompt = PROMPT_LIBRARY[content_type]
    print(f"  [synthesize] running {content_type} synthesis prompt...")
    response = _run_ask(notebook_id, prompt)
    if not response:
        raise RuntimeError("NotebookLM returned an empty response — try re-running after sources finish processing")

    today = datetime.now().strftime("%Y-%m-%d")
    topic_slug = to_kebab(topic)

    tag_block = "  - synthesis\n  - youtube/" + topic_slug
    themes_block = ""
    if themes:
        themes_block = "themes:\n" + "\n".join(f"  - {t}" for t in themes) + "\n"

    frontmatter = (
        f"---\n"
        f"tags:\n{tag_block}\n"
        f"date: {today}\n"
        f"source-type: {content_type}\n"
        f"topic: \"{topic}\"\n"
        f"{themes_block}"
        f"---\n\n"
    )

    source_links = ""
    resources_dir = topic_dir / "topic-resources"
    if resources_dir.exists():
        sources = sorted(resources_dir.glob("*.md"))
        if sources:
            source_links = "\n\n## Sources\n" + "\n".join(
                f"- [[topic-resources/{s.stem}]]" for s in sources
            )

    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    out_path = topic_dir / f"synthesis-{timestamp}.md"
    out_path.write_text(frontmatter + response + source_links, encoding="utf-8")
    print(f"  [saved] {out_path.name}")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Convert YouTube transcripts and synthesize via NotebookLM into Obsidian notes."
    )
    parser.add_argument(
        "--topic",
        required=True,
        help='Topic name (e.g. "Guitar Rigs"). Creates/reuses a folder and NotebookLM notebook.',
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT),
        help=f'Root folder for all topic output. Defaults to ./youtube_summary next to this script.',
    )
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="One or more .txt transcript files downloaded from YouTube.",
    )
    args = parser.parse_args()

    summary_root = Path(args.output_dir)
    topic_dir = summary_root / args.topic
    topic_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== yt-summarize: '{args.topic}' ===\n")

    # Step 1: convert
    print("[1/5] Converting transcripts...")
    for file_arg in args.files:
        txt_path = Path(file_arg)
        if not txt_path.exists():
            print(f"  [warn] file not found: {file_arg}", file=sys.stderr)
            continue
        if txt_path.suffix.lower() != ".txt":
            print(f"  [warn] expected .txt, got: {file_arg}", file=sys.stderr)
        convert_txt_to_md(txt_path, topic_dir)

    # Step 2: notebook
    print("\n[2/5] Resolving NotebookLM notebook...")
    notebook_id = get_or_create_notebook(args.topic, topic_dir)

    # Step 3: sources
    print("\n[3/5] Syncing sources to NotebookLM...")
    sync_sources(notebook_id, topic_dir)

    # Step 4: classify
    print("\n[4/5] Classifying content type...")
    content_type, themes = classify_content(notebook_id)

    # Step 5: synthesize
    print("\n[5/5] Synthesizing...")
    result_path = synthesize(notebook_id, topic_dir, args.topic, content_type, themes)

    print(f"\nDone. Synthesis saved to:\n  {result_path}\n")


if __name__ == "__main__":
    main()
