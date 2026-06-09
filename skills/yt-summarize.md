# Skill: YT Summarize

Convert YouTube videos into a synthesized Obsidian study note + action file via NotebookLM.

---

## Trigger

User wants to summarize YouTube videos, mentions transcript files, says "yt-summarize," "summarize these videos," or "add to [topic]."

## What It Does

1. **Collect inputs** — identify from the conversation:
   - `--topic`: the study topic (e.g. `"Guitar Rigs"`). Ask if missing.
   - URLs are read from `main/AIOS/youtube_summary/Video Queue.md` under the matching `## Topic` heading. No file paths needed.

2. **Run the tool** via Bash:

   ```bash
   py -3 "C:\Users\haden\Documents\Synced_Vault\main\AIOS\Skills\yt-summarize.py" --topic "TOPIC"
   ```

3. **Report the result** — tell the user where both output files landed:
   ```
   main/AIOS/youtube_summary/<Topic>/<topic-slug>-synthesis-YYYY-MM-DD-HHMM.md
   main/AIOS/youtube_summary/<Topic>/<topic-slug>-action-YYYY-MM-DD-HHMMSS.md
   ```

## Video Queue

Videos to analyze are stored in `main/AIOS/youtube_summary/Video Queue.md`.
Format: one `##` heading per topic, raw YouTube URLs pasted as plain lines underneath.

```
## Guitar Rigs
https://www.youtube.com/watch?v=xxx
https://www.youtube.com/watch?v=yyy
```

Ask the user to paste URLs under the correct heading before running if they haven't yet.

## Workflows

- **New topic:** add URLs under a new `## Heading` in Video Queue.md, run with the topic name
- **Add to existing topic:** add more URLs under the existing heading and re-run — already-processed transcripts and sources are skipped automatically
- **Re-synthesize only:** pass any already-converted `.md` path as a file argument:
  ```bash
  py -3 "...\yt-summarize.py" --topic "Guitar Rigs" "path\to\converted.md"
  ```

## Principles

- Ask at most one clarifying question. If topic is present and queue has URLs, run immediately.
- Topic name is case-sensitive and determines the folder name. Preserve the user's capitalization.
- The tool is idempotent — re-running is always safe.
- Full usage docs at: `main/AIOS/youtube_summary/Help/how-to-use.md`
