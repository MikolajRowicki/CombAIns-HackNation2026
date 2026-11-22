"""Trim the silence at the edges of each narration clip, apply one tempo, write WAV files and durations.json."""

import json
import subprocess
import sys
import wave
from pathlib import Path

import imageio_ffmpeg

OUT = Path(__file__).resolve().parents[2] / "data" / "cache" / "video"
FF = imageio_ffmpeg.get_ffmpeg_exe()
TEMPO = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
TRIM = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05"
out = {}
for i in range(1, 10):
    sid = f"s{i}"
    wav = OUT / "audio" / f"{sid}.wav"
    chain = f"{TRIM},areverse,{TRIM},areverse,atempo={TEMPO}"
    subprocess.run(
        [FF, "-y", "-loglevel", "error", "-i", str(OUT / "audio" / f"{sid}.mp3"), "-af", chain, "-ar", "44100", "-ac", "1", str(wav)],
        check=True,
    )
    with wave.open(str(wav)) as w:
        out[sid] = round(w.getnframes() / w.getframerate(), 2)
(OUT / "durations.json").write_text(json.dumps(out))
print(out, round(sum(out.values()), 1))
