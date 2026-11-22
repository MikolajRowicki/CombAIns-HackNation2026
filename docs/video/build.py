"""Join the screencast frames and the narration clips into one MP4 file."""

import array
import json
import subprocess
import tempfile
import wave
from pathlib import Path

import imageio_ffmpeg

OUT = Path(__file__).resolve().parents[2] / "data" / "cache" / "video"
FRAMES = Path(tempfile.gettempdir()) / "radar_video_frames"
LIMIT = 180  # The task allows a video of 3 minutes or less.
FF = imageio_ffmpeg.get_ffmpeg_exe()
RATE = 44100

data = json.loads((OUT / "frames.json").read_text())
frames, end = data["frames"], data["end"]
timeline = json.loads((OUT / "timeline.json").read_text())
t0 = frames[0][0]
total = end - t0

lines = []
for i, (ts, name) in enumerate(frames):
    nxt = frames[i + 1][0] if i + 1 < len(frames) else end
    lines.append(f"file '{(FRAMES / name).as_posix()}'\nduration {max(nxt - ts, 0.001):.4f}")
lines.append(f"file '{(FRAMES / frames[-1][1]).as_posix()}'")
(OUT / "frames.txt").write_text("\n".join(lines) + "\n")

track = array.array("h", bytes(2 * int((total + 0.5) * RATE)))
for seg in timeline:
    with wave.open(str(OUT / "audio" / f"{seg['id']}.wav")) as w:
        assert w.getframerate() == RATE and w.getnchannels() == 1 and w.getsampwidth() == 2
        clip = array.array("h", w.readframes(w.getnframes()))
    offset = int((seg["start"] - t0) * RATE)
    track[offset : offset + len(clip)] = clip
    print(seg["id"], f"{seg['start'] - t0:6.2f} s")
with wave.open(str(OUT / "narration.wav"), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(track.tobytes())

out = OUT / "Radar_innowacji_demo.mp4"
fade_out = total - 0.8
subprocess.run(
    [
        FF, "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(OUT / "frames.txt"),
        "-i", str(OUT / "narration.wav"),
        "-vf", f"scale=1920:1080:flags=lanczos,fps=30,format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out:.2f}:d=0.8",
        "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}",
        str(out),
    ],
    check=True,
    cwd=OUT,
)
print(f"{out.name}: {total:.1f} s, {out.stat().st_size / 1e6:.1f} MB")
if total > LIMIT:
    print(f"WARNING: the video is longer than {LIMIT} s. Close other programs and record again.")
