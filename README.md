# obsidian-YT-notes

Converts YouTube transcript files into structured Obsidian study notes using NotebookLM.

The tool classifies each batch of videos by content type (tutorial, lecture, interview, narrative, opinion), selects the appropriate synthesis prompt, and outputs a markdown note with Obsidian YAML frontmatter, `[[wikilinks]]` on key concepts, and a Sources section that creates backlinks to the original transcripts.

---

## What you get

```markdown
---
tags:
  - synthesis
  - youtube/guitar-rigs
date: 2026-06-08
source-type: tutorial
topic: "Guitar Rigs"
themes:
  - signal chain, amp selection, pedal order, tone shaping
---

## Overview
...body with [[wikilinks]] on key concepts...

## Sources
- [[topic-resources/knocked-loose-rig-rundown]]
- [[topic-resources/intervals-rig-rundown]]
```

---

## Requirements

- Python 3.10+
- `notebooklm` CLI — install and authenticate with `notebooklm login`
- A Google account with NotebookLM access
- YouTube transcripts as `.txt` files (the [YouTube Transcript](https://chromewebstore.google.com/detail/youtube-transcript/engkpczbmpjkbbfgkbnoapbbpmhbfind) Chrome extension works well)

---

## Quick start

```bash
py -3 yt-summarize.py \
  --topic "Guitar Rigs" \
  --output-dir "/path/to/your/vault/youtube_summary" \
  "~/Downloads/Video One - YouTube.txt" \
  "~/Downloads/Video Two - YouTube.txt"
```

Output lands at `<output-dir>/Guitar Rigs/synthesis-YYYY-MM-DD-HHMM.md`.

Omit `--output-dir` to write to `youtube_summary/` next to the script.

Full usage, workflows, and troubleshooting: [`docs/how-to-use.md`](docs/how-to-use.md)

---

## Using with Claude Code

Copy `skills/yt-summarize.md` to your Claude skills directory. Add the contents
of `CLAUDE.md` to your project's CLAUDE.md. Then tell Claude:

> "Summarize these videos for a topic called Guitar Rigs"

Claude will handle the rest.

---

## Content types

| Type | Used for |
|------|----------|
| `tutorial` | How-to, step-by-step, workflows |
| `lecture` | Conceptual, theory, frameworks |
| `interview` | Conversations, multiple speakers |
| `narrative` | Stories, case studies, journeys |
| `opinion` | Arguments, critiques, essays |
| `mixed` | Combinations of the above |

The type is auto-detected per run and stored in the note's `source-type` frontmatter field.
