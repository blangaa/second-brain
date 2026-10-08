#!/usr/bin/env python3
"""Transcribe audio files from inbox/ into Markdown notes in notes/."""

from datetime import datetime
from pathlib import Path
import json
import subprocess
import re
from datetime import datetime, timezone

import mlx_whisper

# --- Configuration -----------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
INBOX = BASE_DIR / "data" / "inbox"
NOTES = BASE_DIR / "data" / "notes"
VOCAB_FILE = BASE_DIR / "config" / "vocabulary.txt"
CORRECTIONS_FILE = BASE_DIR / "config" / "corrections.txt"
MODEL = "mlx-community/whisper-large-v3-turbo"
LANGUAGE = "es"
AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".aac", ".flac"}
PARAGRAPH_GAP_SECONDS = 0.95  # a pause longer than this starts a new paragraph


def load_vocabulary() -> str | None:
    """Return the vocabulary prompt, or None if the file doesn't exist."""
    if VOCAB_FILE.exists():
        return VOCAB_FILE.read_text(encoding="utf-8").strip() or None
    return None

def load_corrections() -> list[tuple[str, str]]:
    """Read 'wrong -> right' pairs from config/corrections.txt."""
    if not CORRECTIONS_FILE.exists():
        return []
    pairs = []
    for line in CORRECTIONS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "->" not in line:
            continue
        wrong, right = (part.strip() for part in line.split("->", 1))
        pairs.append((wrong, right))
    return pairs


def apply_corrections(text: str, pairs: list[tuple[str, str]]) -> str:
    """Replace each wrong form with its right form (case-insensitive)."""
    for wrong, right in pairs:
        text = re.sub(re.escape(wrong), right, text, flags=re.IGNORECASE)
    return text

def build_paragraphs(segments: list[dict]) -> str:
    """Join Whisper segments into paragraphs, splitting on long pauses."""
    paragraphs: list[list[str]] = []
    previous_end = None
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        is_new_paragraph = (
            previous_end is None
            or seg["start"] - previous_end > PARAGRAPH_GAP_SECONDS
        )
        if is_new_paragraph:
            paragraphs.append([text])
        else:
            paragraphs[-1].append(text)
        previous_end = seg["end"]
    return "\n\n".join(" ".join(p) for p in paragraphs)

def read_audio_metadata(audio: Path) -> dict:
    """Return container tags from ffprobe, or {} if unavailable."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", str(audio)],
            capture_output=True, text=True, check=True,
        ).stdout
        return json.loads(out).get("format", {}).get("tags", {})
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return {}


def recording_time(audio: Path, tags: dict) -> datetime:
    """Real recording time in local timezone; falls back to file mtime."""
    raw = tags.get("creation_time")
    if raw:
        utc = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return utc.astimezone()  # convert to the machine's local timezone
    return datetime.fromtimestamp(audio.stat().st_mtime)

def build_markdown(audio: Path, result: dict) -> str:
    """Build the note: YAML frontmatter + transcript."""
    segments = result["segments"]
    duration_s = int(segments[-1]["end"]) if segments else 0
    tags = read_audio_metadata(audio)
    recorded = recording_time(audio, tags)
    voice_memo_id = tags.get("voice-memo-uuid", "")

    frontmatter = (
        "---\n"
        f"title: {audio.stem}\n"
        f"recorded: {recorded:%Y-%m-%d %H:%M}\n"
        f"duration: {duration_s // 60}m{duration_s % 60:02d}s\n"
        f"source: {audio.name}\n"
        f"audio_id: {voice_memo_id}\n"
        f"language: {result.get('language', LANGUAGE)}\n"
        f"model: {MODEL}\n"
        "status: transcribed\n"
        "tags: []\n"
        "summary: \n"
        "---\n\n"
    )
    transcript = apply_corrections(build_paragraphs(segments), load_corrections())
    return frontmatter + "## Transcript\n\n" + transcript + "\n"


def process(audio: Path, vocabulary: str | None) -> None:
    output = NOTES / f"{audio.stem}.md"
    print(f"Transcribing {audio.name} ...")
    result = mlx_whisper.transcribe(
        str(audio),
        path_or_hf_repo=MODEL,
        language=LANGUAGE,
        initial_prompt=vocabulary,
    )
    output.write_text(build_markdown(audio, result), encoding="utf-8")
    print(f"  -> {output.relative_to(BASE_DIR)}")


def main() -> None:
    NOTES.mkdir(parents=True, exist_ok=True)
    vocabulary = load_vocabulary()
    pending = [
        f for f in sorted(INBOX.iterdir())
        if f.suffix.lower() in AUDIO_EXTENSIONS
        and not (NOTES / f"{f.stem}.md").exists()
    ]
    if not pending:
        print("Nothing to do: no new audio files in data/inbox/.")
        return
    for audio in pending:
        process(audio, vocabulary)


if __name__ == "__main__":
    main()
