# yt-summarize: How to Use

Converts YouTube videos into two Obsidian notes per run: a structured synthesis note
and an action analysis note. Uses NotebookLM to classify content type, select prompts,
and generate both outputs.

---

## Setup (first time only)

Install the transcript fetching dependency:

```bash
pip install youtube-transcript-api
```

---

## Using via Claude (recommended)

Tell Claude what you want:

> "Summarize these videos for a topic called Guitar Rigs"
> "Add this video to my Max for Live notes"
> "yt-summarize — Guitar Rigs"

Claude will check the Video Queue, ask for anything missing, run the tool, and report
where both output files landed.

Skill file: `main/AIOS/Skills/yt-summarize.md`

---

## Video Queue

All videos are managed through one file:
`main/AIOS/youtube_summary/Video Queue.md`

Add URLs as plain lines under a `##` heading matching your topic name:

```
## Guitar Rigs
https://www.youtube.com/watch?v=xxx
https://www.youtube.com/watch?v=yyy
```

When you run the tool with `--topic "Guitar Rigs"`, it reads all URLs under that heading,
fetches transcripts automatically, and processes them. No browser extension, no manual downloads.

---

## Using via command line (manual)

```bash
py -3 "C:\Users\haden\Documents\Synced_Vault\main\AIOS\Skills\yt-summarize.py" --topic "Your Topic Name"
```

---

## Workflow A: New topic, first batch of videos

**Step 1 — Add URLs to Video Queue**

Open `main/AIOS/youtube_summary/Video Queue.md`.
Add a new `##` heading for your topic and paste in the YouTube URLs:

```
## DSP Basics
https://www.youtube.com/watch?v=aaa
https://www.youtube.com/watch?v=bbb
```

**Step 2 — Run the tool**

```bash
py -3 "C:\Users\haden\Documents\Synced_Vault\main\AIOS\Skills\yt-summarize.py" --topic "DSP Basics"
```

**Step 3 — Find your notes**

Two files are created:
```
main/AIOS/youtube_summary/DSP Basics/synthesis-YYYY-MM-DD-HHMM.md
main/AIOS/youtube_summary/DSP Basics/action-YYYY-MM-DD-HHMMSS.md
```

The **synthesis** note includes YAML frontmatter, body structured for the detected content
type (tutorial, lecture, interview, narrative, opinion, or mixed), `[[wikilinks]]` on key
concepts, and source backlinks.

The **action** note contains a type-adapted follow-up — implementation checklist,
concept application guide, follow-up research map, lesson extraction, position evaluation,
or prioritized next actions depending on what the synthesis looked like.

---

## Workflow B: Adding videos to an existing topic

Add more URLs under the same `##` heading in Video Queue.md and re-run with the same topic name.
Already-converted transcripts and already-uploaded sources are skipped automatically.
A new `synthesis-*.md` and `action-*.md` pair is produced. Previous files are untouched.

---

## Workflow C: Re-synthesizing without adding new videos

Pass any already-converted `.md` file from the topic folder directly:

```bash
py -3 "C:\Users\haden\Documents\Synced_Vault\main\AIOS\Skills\yt-summarize.py" ^
  --topic "Guitar Rigs" ^
  "C:\Users\haden\Documents\Synced_Vault\main\AIOS\youtube_summary\Guitar Rigs\knocked-loose-rig-rundown.md"
```

The tool skips fetching and uploading, runs a fresh synthesis + action pass.

---

## Folder structure

```
main/AIOS/youtube_summary/
├── Video Queue.md             ← paste URLs here, organized by ## heading
├── Help/
│   └── how-to-use.md          ← you are here
├── Guitar Rigs/
│   ├── notebook-id.txt        ← NotebookLM notebook ID — do not edit
│   ├── topic-resources/
│   │   ├── knocked-loose-rig-rundown.md    ← fetched transcript
│   │   └── another-rig-rundown.md          ← fetched transcript
│   ├── synthesis-2026-06-08-1430.md        ← structured synthesis note
│   └── action-2026-06-08-143012.md         ← action analysis note
```

---

## Renaming a topic folder

Safe to rename in Obsidian or Explorer. The `notebook-id.txt` travels with the folder.
After renaming, use the new folder name as `--topic` in future runs and update the
`##` heading in `Video Queue.md` to match.

---

## Troubleshooting

**`youtube_transcript_api` not found**
Run: `pip install youtube-transcript-api`

**`TranscriptsDisabled` or `NoTranscriptFound`**
The video has no available transcript (disabled by the uploader, or auto-captions unavailable).
Try a different video.

**`notebooklm: command not found`**
The CLI isn't on your PATH. Find where it's installed and add that directory to PATH, or use the full path.

**`notebooklm error: 401 Unauthorized`**
Your session expired. Run `notebooklm login` and re-authenticate.

**Second pass failed warning**
The synthesis was still saved — check the warning message. Common cause: NotebookLM rate limit
after back-to-back requests. Re-run using Workflow C to generate a fresh action note.

**`[error] failed to upload 'video.md'`**
NotebookLM occasionally rejects uploads. Re-run — already-uploaded sources are skipped, only the failed one retries.

**Synthesis is generic or misses key points**
NotebookLM needs time to process newly uploaded sources. Wait a minute and re-run via Workflow C.

**`notebook-id.txt` shows a deleted notebook warning**
The notebook was deleted. The tool auto-creates a new one and re-uploads all sources.
This run will take longer than normal.
