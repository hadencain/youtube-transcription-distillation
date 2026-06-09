#!/usr/bin/env python3
"""yt-summarize: convert YouTube transcripts and synthesize via NotebookLM."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

VAULT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SUMMARY_ROOT = VAULT_ROOT / "main" / "AIOS" / "youtube_summary"

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

ACTION_PROMPT_LIBRARY = {
    "tutorial": (
        "Based on this synthesis note, create an implementation checklist. Structure it as:\n"
        "1. A one-sentence statement of what you are implementing\n"
        "2. Ordered concrete steps to apply what was learned — specific and actionable\n"
        "3. Prerequisites or setup required before starting\n"
        "4. Success criteria — how you will know it worked\n\n"
        "Write for doing, not reading. No filler. No intro or outro sentences about the note itself."
    ),
    "lecture": (
        "Based on this synthesis note, create a concept application guide. Structure it as:\n"
        "1. The core framework restated in one sentence\n"
        "2. Where and how to apply each key concept in practice\n"
        "3. Specific situations where this knowledge changes a decision or action\n"
        "4. One immediate experiment or test to try\n\n"
        "Write for application, not review. No intro or outro sentences about the note itself."
    ),
    "interview": (
        "Based on this synthesis note, create a follow-up research map. Structure it as:\n"
        "1. The most important insight worth pursuing further\n"
        "2. Specific people, tools, books, or resources to investigate\n"
        "3. Open questions raised by the content\n"
        "4. One concrete next step\n\n"
        "Write for action, not summary. No intro or outro sentences about the note itself."
    ),
    "narrative": (
        "Based on this synthesis note, extract actionable lessons. Structure it as:\n"
        "1. What to replicate — patterns or decisions worth adopting\n"
        "2. What to avoid — pitfalls or anti-patterns demonstrated\n"
        "3. What generalizes beyond this specific case\n"
        "4. One immediate thing to apply or test\n\n"
        "Write for pattern recognition. No intro or outro sentences about the note itself."
    ),
    "opinion": (
        "Based on this synthesis note, create a position evaluation. Structure it as:\n"
        "1. The central claim, restated plainly\n"
        "2. Where you agree and why\n"
        "3. Where you disagree or need more evidence\n"
        "4. What to investigate to resolve the uncertainty\n\n"
        "Separate claim from evidence. No intro or outro sentences about the note itself."
    ),
    "mixed": (
        "Based on this synthesis note, create a prioritized action list. Structure it as:\n"
        "1. The top 3 actionable insights, ranked by impact\n"
        "2. Concrete next steps for each\n"
        "3. Any dependencies or prerequisites\n"
        "4. What to do first\n\n"
        "Write for immediate use. No filler. No intro or outro sentences about the note itself."
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


QUEUE_FILE = SUMMARY_ROOT / "Video Queue.md"


def parse_queue_text(text: str, topic: str) -> list[str]:
    """Return URLs under the matching ## topic heading. Case-insensitive match. Stops at next heading."""
    urls = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line[3:].strip().lower() == topic.lower()
            continue
        if in_section:
            stripped = line.strip()
            if stripped.startswith("http"):
                urls.append(stripped)
    return urls


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from watch?v= or youtu.be/ URLs. Raises ValueError if not found."""
    match = re.search(r"(?:v=|youtu\.be/)([^&\n?#]+)", url)
    if not match:
        raise ValueError(f"Could not extract video ID from URL: {url}")
    return match.group(1)


def get_video_title(video_id: str) -> str:
    """Fetch video title from YouTube page. Falls back to video_id on any error."""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        match = re.search(r"<title>(.+?) - YouTube</title>", html)
        if match:
            return match.group(1)
    except Exception:
        pass
    return video_id


def fetch_transcript_text(video_id: str) -> str:
    """Fetch transcript from YouTube via youtube-transcript-api. Returns newline-joined text."""
    if YouTubeTranscriptApi is None:
        raise ImportError("youtube-transcript-api not installed. Run: pip install youtube-transcript-api")
    transcript = YouTubeTranscriptApi().fetch(video_id)
    return "\n".join(entry.text for entry in transcript)


def write_transcript_md(title: str, content: str, topic_dir: Path) -> Path:
    """Write transcript as .md into topic-resources/. Skips if file already exists."""
    resources_dir = topic_dir / "topic-resources"
    resources_dir.mkdir(exist_ok=True)
    md_path = resources_dir / (to_kebab(title) + ".md")
    if md_path.exists():
        print(f"  [skip] {md_path.name} already exists")
        return md_path
    md_path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
    print(f"  [fetched] {title} → {md_path.name}")
    return md_path


def fetch_transcripts_from_queue(topic: str, topic_dir: Path) -> None:
    """Read URLs under ## topic from Video Queue.md and fetch transcripts for each."""
    if not QUEUE_FILE.exists():
        raise FileNotFoundError(
            f"Queue file not found at {QUEUE_FILE}\n"
            f"Create it or pass transcript files directly as arguments."
        )
    text = QUEUE_FILE.read_text(encoding="utf-8")
    urls = parse_queue_text(text, topic)
    if not urls:
        print(f"  [warn] no URLs found under '## {topic}' in Video Queue.md", file=sys.stderr)
        return
    print(f"  [queue] found {len(urls)} URL(s) under '## {topic}'")
    for url in urls:
        try:
            video_id = extract_video_id(url)
            title = get_video_title(video_id)
            print(f"  [fetch] {title}")
            content = fetch_transcript_text(video_id)
            write_transcript_md(title, content, topic_dir)
        except Exception as e:
            print(f"  [error] {url}: {e}", file=sys.stderr)


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

    # Build Obsidian YAML frontmatter
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

    # Wikilinked source list — creates backlinks on each source note in Obsidian
    source_links = ""
    resources_dir = topic_dir / "topic-resources"
    if resources_dir.exists():
        sources = sorted(resources_dir.glob("*.md"))
        if sources:
            source_links = "\n\n## Sources\n" + "\n".join(
                f"- [[topic-resources/{s.stem}]]" for s in sources
            )

    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    out_path = topic_dir / f"{topic_slug}-synthesis-{timestamp}.md"
    out_path.write_text(frontmatter + response + source_links, encoding="utf-8")
    print(f"  [saved] {out_path.name}")
    return out_path


def run_second_pass(synthesis_path: Path, topic: str, content_type: str) -> Path:
    """Create temp NotebookLM notebook, upload synthesis, run action prompt, save action file, delete notebook."""
    if not synthesis_path.exists():
        raise FileNotFoundError(f"Synthesis file not found: {synthesis_path}")

    timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
    temp_topic = f"_temp_action_{timestamp_str}"
    print(f"  [second-pass] creating temp notebook (will auto-delete)...")
    data = _run_notebooklm(["create", temp_topic])
    temp_notebook_id = data["notebook"]["id"]

    try:
        print(f"  [second-pass] uploading synthesis as source...")
        title = synthesis_path.stem
        _upload_source(temp_notebook_id, synthesis_path, title)

        prompt = ACTION_PROMPT_LIBRARY[content_type]
        print(f"  [second-pass] running {content_type} action prompt...")
        response = _run_ask(temp_notebook_id, prompt)
        if not response:
            raise RuntimeError("Second pass returned an empty response")

        today = datetime.now().strftime("%Y-%m-%d")
        topic_slug = to_kebab(topic)
        frontmatter = (
            f"---\n"
            f"tags:\n  - action\n  - youtube/{topic_slug}\n"
            f"date: {today}\n"
            f"source-type: {content_type}\n"
            f"topic: \"{topic}\"\n"
            f"synthesis: \"[[{synthesis_path.stem}]]\"\n"
            f"---\n\n"
        )

        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        action_path = synthesis_path.parent / f"{topic_slug}-action-{timestamp}.md"
        action_path.write_text(frontmatter + response, encoding="utf-8")
        print(f"  [saved] {action_path.name}")
        return action_path

    finally:
        print(f"  [second-pass] deleting temp notebook...")
        try:
            subprocess.run(
                ["notebooklm", "delete", "-n", temp_notebook_id, "-y"],
                capture_output=True,
            )
        except Exception as e:
            print(f"  [warn] could not delete temp notebook {temp_notebook_id}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Convert YouTube transcripts and synthesize via NotebookLM."
    )
    parser.add_argument(
        "--topic",
        required=True,
        help='Topic name (e.g. "Guitar Rigs"). Creates/reuses a folder and NotebookLM notebook.',
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="Optional .txt transcript files. If omitted, URLs are read from Video Queue.md.",
    )
    args = parser.parse_args()

    topic_dir = SUMMARY_ROOT / args.topic
    topic_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== yt-summarize: '{args.topic}' ===\n")

    # Step 1: fetch/convert
    if args.files:
        print("[1/7] Converting transcripts...")
        for file_arg in args.files:
            txt_path = Path(file_arg)
            if not txt_path.exists():
                print(f"  [warn] file not found: {file_arg}", file=sys.stderr)
                continue
            if txt_path.suffix.lower() != ".txt":
                print(f"  [warn] expected .txt, got: {file_arg}", file=sys.stderr)
            convert_txt_to_md(txt_path, topic_dir)
    else:
        print("[1/7] Fetching transcripts from Video Queue...")
        fetch_transcripts_from_queue(args.topic, topic_dir)

    # Step 2: notebook
    print("\n[2/7] Resolving NotebookLM notebook...")
    notebook_id = get_or_create_notebook(args.topic, topic_dir)

    # Step 3: sources
    print("\n[3/7] Syncing sources to NotebookLM...")
    sync_sources(notebook_id, topic_dir)

    # Step 4: classify
    print("\n[4/7] Classifying content type...")
    content_type, themes = classify_content(notebook_id)

    # Step 6: synthesize
    print("\n[6/7] Synthesizing...")
    result_path = synthesize(notebook_id, topic_dir, args.topic, content_type, themes)

    # Step 7: second pass
    print("\n[7/7] Running second pass action analysis...")
    try:
        action_path = run_second_pass(result_path, args.topic, content_type)
        print(f"\nDone.\n  Synthesis: {result_path}\n  Action:    {action_path}\n")
    except Exception as e:
        print(f"\n  [warn] second pass failed: {e} — synthesis still saved", file=sys.stderr)
        print(f"\nDone. Synthesis saved to:\n  {result_path}\n")


if __name__ == "__main__":
    main()
