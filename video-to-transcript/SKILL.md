---
name: video-to-transcript
description: Use when the user wants to convert a local video or meeting recording into a text transcript, especially MP4/MOV recordings. Covers extracting audio with ffmpeg and transcribing locally with faster-whisper.
---

# Video To Transcript

Use this workflow to convert a local video file into a timestamped text transcript.

## Prerequisites

Check that `ffmpeg` and Python are available:

```bash
which ffmpeg
which python3
```

If Python package installation is needed, use a project-local virtual environment rather than system Python.

## Workflow

1. Create a working folder.

```bash
mkdir -p transcript_output
```

2. Extract the audio from the video as mono 16 kHz WAV.

```bash
ffmpeg -y -i "/absolute/path/to/video.mp4" \
  -vn -ac 1 -ar 16000 -c:a pcm_s16le \
  transcript_output/audio.wav
```

Use the exact input video path provided by the user. The output WAV is a temporary helper file.

3. Create and prepare a local Python virtual environment.

```bash
python3 -m venv .venv_transcript
.venv_transcript/bin/pip install --quiet faster-whisper
```

If the system Python is externally managed, do not use `--break-system-packages`; the local venv avoids that problem.

4. Transcribe with `faster-whisper`.

```bash
.venv_transcript/bin/python - <<'PY'
from faster_whisper import WhisperModel
from pathlib import Path

audio_path = "transcript_output/audio.wav"
out_path = Path("transcript_output/transcript.txt")

model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe(
    audio_path,
    beam_size=5,
    vad_filter=True,
)

with out_path.open("w", encoding="utf-8") as f:
    f.write(f"Language: {info.language} probability={info.language_probability}\n\n")
    for segment in segments:
        line = f"[{segment.start:07.2f} - {segment.end:07.2f}] {segment.text.strip()}\n"
        print(line, end="")
        f.write(line)

print(f"\nWROTE {out_path}")
PY
```

Model choice:

- Use `small` for a good balance of speed and accuracy on normal meeting recordings.
- Use `tiny` or `base` if CPU transcription is too slow.
- Use `medium` only when accuracy is more important than runtime.

5. Verify the transcript.

```bash
sed -n '1,80p' transcript_output/transcript.txt
wc -l transcript_output/transcript.txt
```

Check that timestamps progress normally and that the detected language makes sense.

6. Clean up helper files when the final transcript is no longer needed locally.

```bash
rm -rf transcript_output/audio.wav .venv_transcript
```

Only delete `transcript_output/transcript.txt` if the user has confirmed it is no longer needed.

## Notes

- For long recordings, the first run can take several minutes because the speech model may need to download and load.
- If the transcript is used to create another artifact, keep the transcript until the artifact is accepted or the user asks for cleanup.
- If the video has no audio stream, inspect it with:

```bash
ffprobe -v error -show_entries stream=index,codec_type,codec_name \
  -of default=nw=1 "/absolute/path/to/video.mp4"
```
