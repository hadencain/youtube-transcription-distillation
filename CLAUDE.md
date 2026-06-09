# yt-summarize — Claude Code Instructions

## Skill

When the user wants to summarize YouTube videos, invoke the skill at `skills/yt-summarize.md` before responding.

Triggers: user mentions transcript files, says "yt-summarize", "summarize these videos", "add to [topic]", or pastes YouTube URLs.

## Script location

```
yt-summarize.py
```

Run with `py -3` on Windows, `python3` on Mac/Linux.

## How it runs

The script resolves its output directory from its own location — no flags needed.
When cloned into a Synced_Vault/main/AIOS/Skills/ layout, outputs land at:

```
<vault_root>/main/AIOS/youtube_summary/<Topic>/
```

## Input modes

**Queue mode (default):** reads YouTube URLs from `Video Queue.md` in the output root, under a `## Topic` heading. Run:

```bash
py -3 yt-summarize.py --topic "Topic"
```

**File mode:** pass one or more `.txt` transcript files directly:

```bash
py -3 yt-summarize.py --topic "Topic" file1.txt file2.txt
```

## Output files

Both are written into `youtube_summary/<Topic>/`:

```
<topic-slug>-synthesis-YYYY-MM-DD-HHMM.md      # Obsidian note with frontmatter
<topic-slug>-action-YYYY-MM-DD-HHMMSS.md        # Second-pass action/checklist note
```

## Video Queue format

```
## Guitar Rigs
https://www.youtube.com/watch?v=xxx
https://www.youtube.com/watch?v=yyy
```

One `##` heading per topic. URLs as plain lines underneath.

## File conventions

- Topic folder names: preserve the user's exact capitalization
- Output filenames: kebab-case, prefixed with topic slug
- Never modify files outside the output directory without confirmation

## Git commits

Write the commit message body only — no AI attribution trailers.
