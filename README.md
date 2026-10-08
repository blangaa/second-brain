# Second Brain

A fully local, privacy-first pipeline that turns voice notes into structured,
searchable knowledge. Audio never leaves your machine.

```
voice note → speech-to-text → local LLM analysis → Markdown → Notion
```

> **Status:** work in progress. Stage 1 (transcription) is working.
> Later stages and a custom hardware recorder are planned.

## Why

Ideas are easiest to capture by voice and easiest to lose afterwards.
This project closes the loop: record anything, and get a clean, tagged,
summarized note without sending your audio to a cloud service.

## Roadmap

| Stage | Description | Status |
|---|---|---|
| 1 | Local transcription with Whisper (MLX) | Done |
| 2 | Local LLM: title, summary, tags, action items | Planned |
| 3 | Notion sync | Planned |
| 4 | Custom hardware recorder (ESP32-S3) | Planned |

## Requirements

- Apple Silicon Mac (developed on an M1, 16 GB RAM)
- macOS, Homebrew, Python 3.12, ffmpeg

## Quick start

```bash
brew install ffmpeg python@3.12
git clone <this-repo> && cd second-brain
python3.12 -m venv .venv && source .venv/bin/activate
pip install mlx-whisper
cp config/vocabulary.example.txt config/vocabulary.txt
cp config/corrections.example.txt config/corrections.txt
# put audio files (.m4a, .mp3, .wav) in data/inbox/
python src/second_brain/transcribe.py
```

Notes appear in `data/notes/` as Markdown with YAML frontmatter.

## Measured performance (M1, 16 GB)

| Model | Audio | Time | Speed |
|---|---|---|---|
| whisper-large-v3-turbo | 2 min 54 s | 8.5 s | ~20x real time |

## Privacy

`data/` and personal config files are git-ignored. Audio, transcripts and
personal vocabulary are never committed.