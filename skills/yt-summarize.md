# Skill: YT Summarize

Convert YouTube transcript files into a synthesized Obsidian study note via NotebookLM.

---

## Trigger

User wants to summarize YouTube videos, mentions transcript files, says "yt-summarize," "summarize these videos," "add to [topic]," or drops `.txt` transcript file paths into the conversation.

## What It Does

1. **Collect inputs** — identify from the conversation:
   - `--topic`: the study topic (e.g. `"Guitar Rigs"`). Ask if missing.
   - `files`: one or more `.txt` transcript paths. Ask if missing.
   - Transcripts from the YouTube transcript Chrome extension download to your Downloads folder with the video title as the filename.

2. **Run the tool** via Bash:

   ```bash
   py -3 "/path/to/yt-summarize.py" \
     --topic "TOPIC" \
     --output-dir "/path/to/your/vault/youtube_summary" \
     "PATH/TO/transcript-one.txt" \
     "PATH/TO/transcript-two.txt"
   ```

   If `--output-dir` is omitted, output goes to `youtube_summary/` next to the script.

3. **Report the result** — tell the user where the synthesis file landed and what content type was detected.

## Workflows

- **New topic:** pass `.txt` files from Downloads + a new topic name
- **Add to existing topic:** pass new `.txt` files + the same topic name used before — already-converted files and already-uploaded sources are skipped automatically
- **Re-synthesize only:** pass any already-converted `.md` path in the topic folder + the same topic name — tool skips conversion and upload, runs a fresh classification and synthesis

## Output format

Each synthesis note includes:
- YAML frontmatter: `tags`, `date`, `source-type`, `topic`, `themes`
- Body structured for the detected content type (tutorial, lecture, interview, narrative, opinion, or mixed) with `[[wikilinks]]` on key concepts
- `## Sources` section with `[[topic-resources/filename]]` links that register as Obsidian backlinks on each source note

## Principles

- Ask at most one clarifying question. If both topic and files are present, run immediately.
- Topic name is case-sensitive and determines the folder name. Preserve the user's capitalization.
- The tool is idempotent — re-running is always safe.
- If the tool errors with `notebooklm: command not found` or `401 Unauthorized`, surface the relevant troubleshooting entry from `docs/how-to-use.md`.
- The `source-type` field in the output frontmatter shows which prompt was selected. If it seems wrong, re-running will re-classify.
