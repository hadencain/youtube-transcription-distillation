# yt-summarize: How to Use

Converts YouTube transcript files into Obsidian notes and uses NotebookLM to
classify the content type, select the best synthesis prompt, and produce a
structured Obsidian note with YAML frontmatter, `[[wikilinks]]`, and source backlinks.

---

## Prerequisites

- Python 3.10+
- The `notebooklm` CLI installed and authenticated (`notebooklm login`)
- A Google account with access to NotebookLM
- The [YouTube Transcript](https://chromewebstore.google.com/detail/youtube-transcript/engkpczbmpjkbbfgkbnoapbbpmhbfind) Chrome extension (or any tool that exports transcripts as `.txt`)

---

## Using via Claude Code (recommended)

If you're using Claude Code, copy `skills/yt-summarize.md` into your Claude skills
directory and add the CLAUDE.md content to your project. Then just tell Claude what you want:

> "Summarize these videos for a topic called Guitar Rigs"
> "Add this transcript to my Max for Live notes"

Claude will ask for anything missing (topic or files), then run the tool and tell
you where the synthesis landed.

---

## Using via command line

### Basic usage

```bash
py -3 yt-summarize.py --topic "Your Topic" transcript-one.txt transcript-two.txt
```

Output goes to `youtube_summary/Your Topic/synthesis-YYYY-MM-DD-HHMM.md` next to the script.

### Writing into an Obsidian vault

```bash
py -3 yt-summarize.py \
  --topic "Guitar Rigs" \
  --output-dir "C:\Users\you\YourVault\notes\youtube" \
  "C:\Users\you\Downloads\Video Title - YouTube.txt"
```

Replace `--output-dir` with any folder inside your vault. The tool will create
`<output-dir>/Guitar Rigs/` and write everything there.

---

## Workflows

### A: New topic, first batch of videos

**Step 1 — Download transcripts**

Open each YouTube video, click the transcript extension, and save the files.
They'll land in your Downloads folder with the video title as the filename.

**Step 2 — Run the tool**

```bash
py -3 yt-summarize.py \
  --topic "Your Topic Name" \
  --output-dir "/path/to/vault/youtube_summary" \
  "~/Downloads/Video Title One - YouTube.txt" \
  "~/Downloads/Video Title Two - YouTube.txt"
```

**Step 3 — Open the note**

```
<output-dir>/Your Topic Name/synthesis-YYYY-MM-DD-HHMM.md
```

The note opens in Obsidian with:
- **YAML frontmatter** — `tags`, `date`, `source-type`, `topic`, `themes`
- **Body** structured for the detected content type (tutorial, lecture, interview,
  narrative, opinion, or mixed) with `[[wikilinks]]` on key concepts
- **Sources section** — `[[topic-resources/filename]]` links that register as
  backlinks on each source note

---

### B: Adding videos to an existing topic

Re-run with new files and the same topic name. The tool skips anything already
processed and runs a fresh synthesis across all sources:

```bash
py -3 yt-summarize.py \
  --topic "Guitar Rigs" \
  --output-dir "/path/to/vault/youtube_summary" \
  "~/Downloads/New Video - YouTube.txt"
```

A new `synthesis-*.md` is created. The previous one is untouched — you have a
versioned history; the newest file is the most complete synthesis.

---

### C: Re-synthesizing without new videos

Pass any already-converted file from the topic folder to trigger a fresh
classification and synthesis without adding new sources:

```bash
py -3 yt-summarize.py \
  --topic "Guitar Rigs" \
  --output-dir "/path/to/vault/youtube_summary" \
  "/path/to/vault/youtube_summary/Guitar Rigs/topic-resources/any-file.md"
```

The tool will warn about the `.md` extension, skip conversion (already exists),
skip upload (already in notebook), and produce a fresh synthesis.

---

## Folder structure

```
youtube_summary/
├── Guitar Rigs/
│   ├── notebook-id.txt              ← NotebookLM notebook ID — do not edit
│   ├── synthesis-2026-06-08-1430.md ← synthesized study note
│   ├── synthesis-2026-06-09-0900.md ← updated synthesis after adding more videos
│   └── topic-resources/
│       ├── knocked-loose-rig-rundown.md
│       └── another-rig-rundown.md
└── Max for Live/
    ├── notebook-id.txt
    └── ...
```

- **`topic-resources/`** — individual transcripts, converted to markdown. Readable on their own.
- **`synthesis-*.md`** — synthesized study notes. Most recent = most complete.
- **`notebook-id.txt`** — internal state. Do not edit or delete unless you want the tool to create a brand-new notebook for that topic.

---

## Content types

The tool classifies each batch of sources before synthesizing. The detected type
is stored in the `source-type` frontmatter field and determines the note structure:

| Type | Used for | Structure |
|------|----------|-----------|
| `tutorial` | How-to, step-by-step, workflows | Overview → procedures → techniques → pitfalls |
| `lecture` | Conceptual, theory, education | Thesis → concepts → frameworks → implications |
| `interview` | Conversations, multiple speakers | Context → themes → agreements → tensions |
| `narrative` | Stories, case studies, journeys | Context → arc → decisions → lessons |
| `opinion` | Arguments, critiques, essays | Thesis → arguments → counterarguments → assessment |
| `mixed` | Combinations of the above | Thematic headers, flowing prose |

If the classification seems wrong, re-run using Workflow C — it re-classifies fresh each time.

---

## Troubleshooting

**`notebooklm: command not found`**
Install the NotebookLM CLI and ensure it's on your PATH. Run `notebooklm login` to authenticate.

**`notebooklm error: 401 Unauthorized`**
Your session expired. Run `notebooklm login` and re-authenticate.

**`[error] failed to upload 'video.md'`**
Re-run the tool — it skips already-uploaded sources and retries the failed one.

**Synthesis output is thin or generic**
NotebookLM needs time to finish processing sources. Wait a minute and re-run using Workflow C.

**Content type was misclassified**
The `source-type` field in the frontmatter shows which prompt was used. Re-run using
Workflow C to re-classify. Classification falls back to `mixed` if it fails.

**`notebook-id.txt` shows a deleted notebook warning**
The notebook was deleted in NotebookLM. The tool creates a new one and re-uploads
all sources — this run will take longer than normal.

**The tool warns about `.md` extension**
Expected behavior in Workflow C when passing an already-converted file. The tool still runs correctly.
