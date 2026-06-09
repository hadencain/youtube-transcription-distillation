# yt-summarize — Claude Code Instructions

## Skill

When the user wants to summarize YouTube videos, invoke the skill at `skills/yt-summarize.md` before responding.

Triggers: user mentions transcript files, says "yt-summarize", "summarize these videos", "add to [topic]", or drops `.txt` paths into the conversation.

## Script location

```
yt-summarize.py
```

Run it with `py -3` on Windows or `python3` on Mac/Linux.

## Output directory

Default output goes to `youtube_summary/` next to the script. To write into an Obsidian vault instead, pass `--output-dir`:

```bash
py -3 yt-summarize.py --topic "Topic" --output-dir "/path/to/vault/folder" file.txt
```

## File conventions

- Output filenames: kebab-case
- Topic folder names: preserve the user's exact capitalization
- Never modify files outside the output directory without confirmation

## Git commits

Write the commit message body only — no AI attribution trailers.
